from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, StateGraph

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

from config import DEFAULT_CONFIG
from agents.websearch_agent import WebSearchAgent


logger = logging.getLogger(__name__)


class QueryState(TypedDict, total=False):
    """Shared state for the LangGraph workflow."""

    query: str
    domain: str
    keywords: List[str]
    keywords_confidence: float
    scraped_articles: List[Dict[str, Any]]
    answer: str
    error: str


_llm: Optional[ChatOllama] = None
_embeddings: Optional[HuggingFaceEmbeddings] = None
_web_agent: Optional[WebSearchAgent] = None


def _get_llm() -> ChatOllama:
    """Create or reuse a ChatOllama instance based on DEFAULT_CONFIG."""

    global _llm
    if _llm is None:
        model_name = getattr(DEFAULT_CONFIG, "LLM_MODEL_NAME", "llama3.2-vision")
        base_url = getattr(DEFAULT_CONFIG, "OLLAMA_HOST", "http://localhost:11434")
        _llm = ChatOllama(model=model_name, base_url=base_url, temperature=0.3)
        logger.info("LangAgents: initialized ChatOllama with model %s", model_name)
    return _llm


def _get_embeddings() -> HuggingFaceEmbeddings:
    """Create or reuse a HuggingFaceEmbeddings instance."""

    global _embeddings
    if _embeddings is None:
        model_name = getattr(DEFAULT_CONFIG, "EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")
        _embeddings = HuggingFaceEmbeddings(model_name=model_name)
        logger.info("LangAgents: initialized HuggingFaceEmbeddings with model %s", model_name)
    return _embeddings


def _get_web_agent() -> WebSearchAgent:
    """Create or reuse the existing WebSearchAgent for search+scrape."""

    global _web_agent
    if _web_agent is None:
        search_cfg = DEFAULT_CONFIG.get_search_config()
        _web_agent = WebSearchAgent(
            max_results_per_query=search_cfg.get("max_results_per_query", 10),
            max_scrape_per_query=search_cfg.get("max_scrape_per_query", 5),
        )
        logger.info(
            "LangAgents: initialized WebSearchAgent (max_results=%s, max_scrape=%s)",
            search_cfg.get("max_results_per_query", 10),
            search_cfg.get("max_scrape_per_query", 5),
        )
    return _web_agent


_COMMON_WORDS = {
    "what",
    "how",
    "when",
    "where",
    "why",
    "who",
    "the",
    "a",
    "an",
    "and",
    "or",
    "but",
    "in",
    "on",
    "at",
    "to",
    "for",
    "of",
    "with",
    "by",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "have",
    "has",
    "had",
    "do",
    "does",
    "did",
    "will",
    "would",
    "could",
    "should",
    "may",
    "might",
    "can",
    "must",
}

_BANNED_KEYWORDS = {
    "today",
    "todays",
    "today's",
    "latest",
    "news",
    "breaking",
    "update",
    "updates",
    "recent",
}


def _simple_keyword_fallback(query: str) -> List[str]:
    """Simple heuristic keyword extraction used when the LLM fails."""

    if not query:
        return []

    words = re.split(r"[\s,\.\?!]+", query.lower())
    keywords: List[str] = []
    for word in words:
        if not word or len(word) <= 2:
            continue
        if word in _COMMON_WORDS or word in _BANNED_KEYWORDS:
            continue
        keywords.append(word)

    if any(t in words for t in ["ai", "artificial", "intelligence", "ml", "machine", "gpt"]):
        for base in ["ai", "artificial intelligence", "machine learning"]:
            if base not in keywords:
                keywords.append(base)

    return keywords[:8]


def _clean_keywords(keywords: List[str], original_query: str) -> List[str]:
    if not keywords:
        return []

    cleaned: List[str] = []
    seen: set[str] = set()

    for kw in keywords:
        k = str(kw).strip().strip("\"'[](){}")
        k = re.sub(r"\s+", " ", k.lower())
        if not k or k in _BANNED_KEYWORDS:
            continue
        if k not in seen:
            seen.add(k)
            cleaned.append(k)

    if any(t in original_query.lower() for t in ["ai", "artificial intelligence", "machine learning"]):
        for base in ["ai", "artificial intelligence", "machine learning"]:
            if base not in cleaned:
                cleaned.append(base)

    return cleaned[:8]


def _parse_keywords_from_llm(response: str, original_query: str) -> List[str]:
    """Parse "Keywords: [...]" style output from the LLM."""

    try:
        lines = response.strip().split("\n")
        raw_keywords: List[str] = []

        for line in lines:
            line = line.strip()
            if line.startswith("Keywords:"):
                text = line.replace("Keywords:", "").strip()
                if text.startswith("[") and text.endswith("]"):
                    text = text[1:-1]
                raw_keywords = [part.strip().strip("\"'") for part in text.split(",") if part.strip()]
                break

        return _clean_keywords(raw_keywords, original_query)
    except Exception:
        return []


KEYWORDS_PROMPT_TEMPLATE = """You are an intelligent keyword extractor. Analyze the user's query and extract the most relevant keywords that would be useful for web search to find CURRENT, UP-TO-DATE information.

Your task is to:
1. Identify the main concepts and topics in the query
2. Extract 3-8 relevant keywords that would help find RECENT and CURRENT information
3. Focus on specific terms, proper nouns, and key concepts
4. For questions about "current" or "who is" - prioritize terms that will find the most recent information
5. Include temporal keywords like "current", "2024", "2025" when appropriate
6. Avoid common words like "what", "how", "the", "is", "elaborate", "explain" etc.
7. For political positions, avoid specific names unless certain they are current
8. Do NOT output generic words like "today", "todays", "latest", "news", "breaking", "updates"

Output Format:
Keywords: [keyword1, keyword2, keyword3, ...]

Query to analyze: {query}
"""


async def extract_keywords_node(state: QueryState) -> QueryState:
    """Node: extract search keywords using ChatOllama via LangChain."""

    query = state.get("query", "").strip()
    if not query:
        return {"keywords": [], "keywords_confidence": 0.0}

    prompt = ChatPromptTemplate.from_template(KEYWORDS_PROMPT_TEMPLATE)
    chain = prompt | _get_llm() | StrOutputParser()

    try:
        raw = await chain.ainvoke({"query": query})
        keywords = _parse_keywords_from_llm(raw, query)
        if not keywords:
            keywords = _simple_keyword_fallback(query)
            confidence = 0.7 if keywords else 0.3
        else:
            confidence = 0.9
        logger.info("LangAgents: extracted %d keywords", len(keywords))
        return {"keywords": keywords, "keywords_confidence": confidence}
    except Exception as exc:
        logger.exception("LangAgents: keyword extraction failed, using fallback: %s", exc)
        keywords = _simple_keyword_fallback(query)
        confidence = 0.7 if keywords else 0.3
        return {
            "keywords": keywords,
            "keywords_confidence": confidence,
            "error": f"keyword_extraction_error: {exc}",
        }


_AI_TERMS = {
    "ai",
    "artificial intelligence",
    "machine learning",
    "deep learning",
    "neural network",
    "robotics",
    "gpt",
    "openai",
}

_GEO_TERMS = {
    "geopolitics",
    "geopolitical",
    "international relations",
    "foreign policy",
    "diplomacy",
    "diplomatic",
    "war",
    "conflict",
    "sanctions",
    "trade war",
}


async def classify_domain_node(state: QueryState) -> QueryState:
    """Node: infer high-level domain from query + keywords."""

    query = state.get("query", "").lower()
    keywords = [k.lower() for k in state.get("keywords", [])]
    text = " ".join([query] + keywords)

    domain = "out-of-domain"
    if any(term in text for term in _AI_TERMS):
        domain = "ai-robotics"
    elif any(term in text for term in _GEO_TERMS):
        domain = "geopolitics"

    logger.info("LangAgents: inferred domain '%s'", domain)
    return {"domain": domain}


async def web_search_node(state: QueryState) -> QueryState:
    """Node: use the existing WebSearchAgent to search and scrape the web."""

    query = state.get("query", "")
    keywords = state.get("keywords", [])
    domain = state.get("domain", "out-of-domain")

    agent = _get_web_agent()
    try:
        articles = await agent.search_and_scrape(query=query, keywords=keywords, domain=domain)
        logger.info("LangAgents: scraped %d articles", len(articles))
        return {"scraped_articles": articles}
    except Exception as exc:
        logger.exception("LangAgents: web search failed: %s", exc)
        return {"scraped_articles": [], "error": f"websearch_error: {exc}"}


RAG_PROMPT_TEMPLATE = """You are an expert assistant focusing on artificial intelligence, software technologies, and geopolitics.

You are given a set of web sources and a user question.

WEB SOURCES:
{sources}

USER QUESTION: {query}

Instructions:
- Use ONLY the information from the web sources above when possible.
- Do not list headlines; synthesize the information into a clear explanation.
- Pull out concrete facts, numbers, and examples from the sources.
- If multiple sources discuss the topic, synthesize them into one coherent answer.
- Cite sources inline as [S1], [S2], etc.
- If the sources are weak or incomplete, briefly say so and then answer using your general knowledge.

Answer:
"""


DIRECT_PROMPT_TEMPLATE = """You are an expert assistant. Answer the user's question using your knowledge.

Question: {query}

Instructions:
- Provide a concise but complete answer.
- If the question depends on very recent events, mention that your answer may not reflect the latest changes.

Answer:
"""


async def answer_node(state: QueryState) -> QueryState:
    """Node: generate an answer using a simple RAG workflow when possible."""

    query = state.get("query", "")
    articles = state.get("scraped_articles", []) or []
    llm = _get_llm()

    # Fallback: no articles, answer directly
    if not articles:
        prompt = ChatPromptTemplate.from_template(DIRECT_PROMPT_TEMPLATE)
        chain = prompt | llm | StrOutputParser()
        try:
            answer = await chain.ainvoke({"query": query})
            return {"answer": answer}
        except Exception as exc:
            logger.exception("LangAgents: direct answer generation failed: %s", exc)
            return {"answer": "I'm sorry, I could not generate an answer at this time.", "error": f"direct_generation_error: {exc}"}

    # Build documents from scraped content
    docs: List[Document] = []
    for idx, art in enumerate(articles, start=1):
        content = str(art.get("content", "")).strip()
        if len(content) < 50:
            continue
        # Keep a manageable slice of each article
        page_content = content[:2000]
        metadata = {
            "source_id": idx,
            "title": art.get("title") or f"Source {idx}",
            "url": art.get("url", ""),
        }
        docs.append(Document(page_content=page_content, metadata=metadata))

    if not docs:
        prompt = ChatPromptTemplate.from_template(DIRECT_PROMPT_TEMPLATE)
        chain = prompt | llm | StrOutputParser()
        try:
            answer = await chain.ainvoke({"query": query})
            return {"answer": answer}
        except Exception as exc:
            logger.exception("LangAgents: direct answer generation (no docs) failed: %s", exc)
            return {"answer": "I'm sorry, I could not generate an answer at this time.", "error": f"direct_generation_error: {exc}"}

    try:
        embeddings = _get_embeddings()
        vs = FAISS.from_documents(docs, embeddings)
        # Retrieve top-k relevant documents
        k = min(5, len(docs))
        retrieved_docs = vs.similarity_search(query, k=k)
    except Exception as exc:
        logger.exception("LangAgents: RAG retrieval failed, falling back to direct answer: %s", exc)
        prompt = ChatPromptTemplate.from_template(DIRECT_PROMPT_TEMPLATE)
        chain = prompt | llm | StrOutputParser()
        try:
            answer = await chain.ainvoke({"query": query})
            return {"answer": answer, "error": f"rag_retrieval_error: {exc}"}
        except Exception as exc2:
            logger.exception("LangAgents: direct answer generation after RAG failure also failed: %s", exc2)
            return {"answer": "I'm sorry, I could not generate an answer at this time.", "error": f"rag_and_direct_error: {exc2}"}

    # Prepare sources text
    sources_blocks: List[str] = []
    for i, doc in enumerate(retrieved_docs, start=1):
        title = doc.metadata.get("title") or f"Source {i}"
        url = doc.metadata.get("url") or ""
        header = f"=== SOURCE {i} ===\nTITLE: {title}\nURL: {url}\n"
        sources_blocks.append(header + doc.page_content)

    sources_text = "\n\n".join(sources_blocks)

    prompt = ChatPromptTemplate.from_template(RAG_PROMPT_TEMPLATE)
    chain = prompt | llm | StrOutputParser()
    try:
        answer = await chain.ainvoke({"query": query, "sources": sources_text})
        return {"answer": answer}
    except Exception as exc:
        logger.exception("LangAgents: RAG generation failed, falling back to direct answer: %s", exc)
        prompt2 = ChatPromptTemplate.from_template(DIRECT_PROMPT_TEMPLATE)
        chain2 = prompt2 | llm | StrOutputParser()
        try:
            answer = await chain2.ainvoke({"query": query})
            return {"answer": answer, "error": f"rag_generation_error: {exc}"}
        except Exception as exc2:
            logger.exception("LangAgents: direct answer generation after RAG failure also failed: %s", exc2)
            return {"answer": "I'm sorry, I could not generate an answer at this time.", "error": f"rag_and_direct_error: {exc2}"}


def build_intellibridge_graph() -> Any:
    """Build and compile the LangGraph workflow.

    The workflow is roughly:
    1. extract_keywords_node
    2. classify_domain_node
    3. web_search_node
    4. answer_node (RAG/direct)

    Returns a compiled LangGraph app that can be used with
    `await app.ainvoke({"query": "..."})`.
    """

    graph = StateGraph(QueryState)

    graph.add_node("extract_keywords", extract_keywords_node)
    graph.add_node("classify_domain", classify_domain_node)
    graph.add_node("web_search", web_search_node)
    graph.add_node("answer", answer_node)

    graph.set_entry_point("extract_keywords")
    graph.add_edge("extract_keywords", "classify_domain")
    graph.add_edge("classify_domain", "web_search")
    graph.add_edge("web_search", "answer")
    graph.add_edge("answer", END)

    return graph.compile()

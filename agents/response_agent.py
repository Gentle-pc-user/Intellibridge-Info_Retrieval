"""
ResponseAgent for generating contextual responses using RAG pipeline
Uses FAISS vector store and Ollama Gemma 3 for retrieval-augmented generation
"""

import asyncio
import json
import logging
import os
import re
from typing import Dict, List, Optional, Any, Tuple
import numpy as np

import faiss
import ollama

from sentence_transformers import SentenceTransformer

from config import DEFAULT_CONFIG
from openai import AsyncOpenAI
from .utils import (
    setup_logging, clean_text, chunk_text, save_json, load_json, 
    format_timestamp, validate_query
)

logger = setup_logging()

class ResponsePrompts:
    """Prompts for the ResponseAgent"""
    
    @staticmethod
    def get_rag_prompt(query: str, context_docs: list) -> str:
        """Generate RAG prompt with context documents"""
        context_text = "\n\n".join([
            f"=== SOURCE {i+1} ===\n"
            f"Title: {doc.get('title', 'No Title')}\n"
            f"Content: {doc.get('content', '')[:900]}\n"
            f"URL: {doc.get('url', 'No URL')}\n"
            for i, doc in enumerate(context_docs[:5])  # Limit to top 5 docs
        ])
        
        return f"""CONTEXT:
{context_text}

QUESTION: {query}

CRITICAL INSTRUCTIONS:
1. You MUST use the information from the web sources provided above to answer the question
2. DO NOT say "the sources do not contain information" or "no information available" 
3. If the sources contain relevant information, you MUST extract and use it
4. Analyze what IS provided in the sources and use that information
5. If multiple sources discuss the topic, synthesize information from all relevant sources
6. Provide specific details, facts, and examples from the sources
7. If sources don't directly answer the question, use related information they do contain
8. NEVER say you cannot answer - always provide the best possible answer using available information

Based on the web sources provided above, please provide a comprehensive answer to the question.

Answer:"""

    @staticmethod
    def get_direct_prompt(query: str) -> str:
        """Generate direct LLM prompt without context"""
        return f"""You are an expert assistant. Answer the user's question using your knowledge.

Question: {query}

Instructions:
- Provide a comprehensive, helpful answer
- Be factual and accurate
- Use your knowledge to give the best possible answer
- Be direct and informative

Answer:"""

class ErrorPrompts:
    """Error handling prompts"""
    
    CLASSIFICATION_ERROR = "I'll analyze your query using my knowledge and provide the best possible answer."
    
    SEARCH_ERROR = "I'll provide a comprehensive response based on my extensive knowledge and reasoning abilities."
    
    RESPONSE_ERROR = "I'll generate a helpful response using my knowledge and reasoning capabilities."
    
    NO_CONTEXT_ERROR = "Based on my knowledge and reasoning, here's what I can tell you:"
    
    OUT_OF_DOMAIN_MESSAGE = "I'll provide a comprehensive answer using my knowledge and expertise across all domains."

class ResponseAgent:
    """Agent responsible for generating contextual responses using RAG"""
    
    def __init__(self, 
                 llm_model_name: str = "llama3.2-vision",
                 embedding_model_name: str = "all-MiniLM-L6-v2",
                 ollama_host: str = "http://localhost:11434",
                 chunk_size: int = 1000,
                 chunk_overlap: int = 200,
                 max_context_length: int = 8000,
                 openai_api_key: Optional[str] = None,
                 openai_model_name: Optional[str] = None):
        """
        Initialize the ResponseAgent
        
        Args:
            llm_model_name: Name of the Ollama model for generation
            embedding_model_name: Name of the embedding model
            ollama_host: Ollama server URL
            chunk_size: Size of text chunks for embedding
            chunk_overlap: Overlap between chunks
            max_context_length: Maximum context length for LLM
        """
        self.llm_model_name = llm_model_name
        self.embedding_model_name = embedding_model_name
        self.ollama_host = ollama_host
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.max_context_length = max_context_length
        
        # Thresholds for RAG vs direct response
        self.large_threshold = 3000  # Use RAG if content > this
        
        # Initialize models
        self.llm_client = None
        self.embedding_model = None
        self.faiss_index = None
        self.document_store = {}  # Store documents with IDs
        self.openai_api_key = openai_api_key or getattr(DEFAULT_CONFIG, "OPENAI_API_KEY", "")
        self.openai_model_name = openai_model_name or getattr(DEFAULT_CONFIG, "OPENAI_MODEL_NAME", "gpt-4o-mini")
        self.openai_client: Optional[AsyncOpenAI] = None
        
        logger.info(f"ResponseAgent initialized with Ollama model: {self.llm_model_name}")
    
    async def _initialize_llm_client(self):
        """Initialize the Ollama client for LLM"""
        if self.llm_client is None:
            try:
                logger.info(f"Initializing Ollama LLM client for model: {self.llm_model_name}")
                
                # Initialize Ollama client
                self.llm_client = ollama.AsyncClient(host=self.ollama_host)
                
                # Check if model is available
                try:
                    models = await self.llm_client.list()
                    # Handle different response structures
                    if 'models' in models:
                        model_list = models['models']
                    else:
                        model_list = models
                    
                    # Extract model names safely
                    model_names = []
                    for model in model_list:
                        if isinstance(model, dict):
                            # Try different possible keys for model name
                            name = model.get('name') or model.get('model') or str(model)
                        else:
                            name = str(model)
                        model_names.append(name)
                    
                    if self.llm_model_name not in model_names:
                        logger.warning(f"LLM model {self.llm_model_name} not found. Available models: {model_names}")
                        logger.info(f"Attempting to pull LLM model {self.llm_model_name}...")
                        await self.llm_client.pull(self.llm_model_name)
                        logger.info(f"Successfully pulled LLM model {self.llm_model_name}")
                    else:
                        logger.info(f"LLM model {self.llm_model_name} is available")
                        
                except Exception as e:
                    logger.error(f"Error checking/pulling LLM model: {e}")
                    # Try to pull the model anyway
                    try:
                        logger.info(f"Attempting to pull LLM model {self.llm_model_name}...")
                        await self.llm_client.pull(self.llm_model_name)
                        logger.info(f"Successfully pulled LLM model {self.llm_model_name}")
                    except Exception as pull_error:
                        logger.error(f"Failed to pull LLM model: {pull_error}")
                        raise
                
                logger.info("Ollama LLM client initialized successfully")
                
            except Exception as e:
                logger.error(f"Failed to initialize Ollama LLM client: {e}")
                raise
    
    async def _load_embedding_model(self):
        """Load the embedding model"""
        if self.embedding_model is None:
            try:
                logger.info(f"Loading embedding model: {self.embedding_model_name}")
                self.embedding_model = SentenceTransformer(self.embedding_model_name)
                logger.info("Embedding model loaded successfully")
                
            except Exception as e:
                logger.error(f"Failed to load embedding model: {e}")
                raise
    
    async def _initialize_faiss_index(self):
        """Initialize FAISS index for vector storage"""
        if self.embedding_model is None:
            await self._load_embedding_model()
        
        # Get embedding dimension
        sample_text = "sample text"
        embedding = self.embedding_model.encode([sample_text])
        dimension = embedding.shape[1]
        
        # Create FAISS index
        self.faiss_index = faiss.IndexFlatIP(dimension)  # Inner product for cosine similarity
        
        logger.info(f"FAISS index initialized with dimension: {dimension}")
    
    def _load_existing_index(self) -> bool:
        """
        Load existing FAISS index and document store
        
        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            index_path = "data/embeddings/faiss_index.bin"
            docs_path = "data/embeddings/document_store.json"
            
            if os.path.exists(index_path) and os.path.exists(docs_path):
                # Load FAISS index
                self.faiss_index = faiss.read_index(index_path)
                
                # Load document store
                self.document_store = load_json(docs_path) or {}
                
                logger.info(f"Loaded existing index with {self.faiss_index.ntotal} vectors")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error loading existing index: {e}")
            return False
    
    def _save_index(self):
        """Save FAISS index and document store"""
        try:
            os.makedirs("data/embeddings", exist_ok=True)
            
            if self.faiss_index is not None:
                index_path = "data/embeddings/faiss_index.bin"
                faiss.write_index(self.faiss_index, index_path)
            
            if self.document_store:
                docs_path = "data/embeddings/document_store.json"
                save_json(self.document_store, docs_path)
            
            logger.info("Index saved successfully")
            
        except Exception as e:
            logger.error(f"Error saving index: {e}")
    
    async def _embed_text(self, text: str) -> np.ndarray:
        """
        Generate embedding for text
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
        """
        if self.embedding_model is None:
            await self._load_embedding_model()
        
        embedding = self.embedding_model.encode([text])
        return embedding[0]
    
    async def _add_documents_to_index(self, documents: List[Dict[str, Any]]):
        """
        Add documents to FAISS index
        
        Args:
            documents: List of documents to add
        """
        if not documents:
            return
        
        try:
            # Initialize index if needed
            if self.faiss_index is None:
                await self._initialize_faiss_index()
            
            # Process documents
            texts_to_embed = []
            doc_metadata = []
            
            for doc in documents:
                content = doc.get('content', '')
                if not content:
                    continue
                
                # Chunk the content
                chunks = chunk_text(content, self.chunk_size, self.chunk_overlap)
                
                for i, chunk in enumerate(chunks):
                    if len(chunk.strip()) > 50:  # Skip very short chunks
                        texts_to_embed.append(chunk)
                        doc_metadata.append({
                            'doc_id': f"{doc.get('url', 'unknown')}_{i}",
                            'chunk_id': i,
                            'title': doc.get('title', ''),
                            'url': doc.get('url', ''),
                            'domain': doc.get('domain', ''),
                            'author': doc.get('author', ''),
                            'date_published': doc.get('date_published', ''),
                            'query': doc.get('query', ''),
                            'keywords': doc.get('keywords', []),
                            'content': chunk
                        })
            
            if not texts_to_embed:
                logger.warning("No valid texts to embed")
                return
            
            # Generate embeddings
            logger.info(f"Generating embeddings for {len(texts_to_embed)} chunks")
            embeddings = self.embedding_model.encode(texts_to_embed)
            
            # Normalize embeddings for cosine similarity
            faiss.normalize_L2(embeddings)
            
            # Add to FAISS index
            self.faiss_index.add(embeddings.astype('float32'))
            
            # Store document metadata
            for i, metadata in enumerate(doc_metadata):
                doc_id = f"{len(self.document_store)}"
                self.document_store[doc_id] = metadata
            
            logger.info(f"Added {len(texts_to_embed)} chunks to index")
            
            # Save index
            self._save_index()
            
        except Exception as e:
            logger.error(f"Error adding documents to index: {e}")
    
    async def _retrieve_relevant_documents(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve relevant documents for query
        
        Args:
            query: Query text
            k: Number of documents to retrieve
            
        Returns:
            List of relevant documents
        """
        try:
            if self.faiss_index is None or self.faiss_index.ntotal == 0:
                logger.warning("No documents in index")
                return []
            
            # Generate query embedding
            query_embedding = await self._embed_text(query)
            query_embedding = np.array([query_embedding], dtype='float32')
            faiss.normalize_L2(query_embedding)
            
            # Search index
            scores, indices = self.faiss_index.search(query_embedding, min(k, self.faiss_index.ntotal))
            
            # Retrieve documents
            relevant_docs = []
            for score, idx in zip(scores[0], indices[0]):
                if idx != -1 and score > 0.3:  # Minimum similarity threshold
                    doc_id = str(idx)
                    if doc_id in self.document_store:
                        doc = self.document_store[doc_id].copy()
                        doc['similarity_score'] = float(score)
                        relevant_docs.append(doc)
            
            logger.info(f"Retrieved {len(relevant_docs)} relevant documents")
            return relevant_docs
            
        except Exception as e:
            logger.error(f"Error retrieving documents: {e}")
            return []
    
    async def _generate_with_llm(self, prompt: str) -> str:
        """
        Generate response using the Ollama LLM
        
        Args:
            prompt: Input prompt
            
        Returns:
            Generated response
        """
        try:
            await self._initialize_llm_client()
            
            # Generate response using Ollama - NO TIMEOUT, let it take as long as needed
            logger.info("Starting LLM generation - no timeout, will wait as long as needed...")
            response = await self.llm_client.generate(
                model=self.llm_model_name,
                prompt=prompt,
                options={
                    'temperature': 0.6,
                    'top_p': 0.9,
                    'num_predict': 512,   # Reduce tokens to lower memory
                    'num_ctx': 1536,      # Smaller context to avoid OOM
                    'num_batch': 1,
                    'num_thread': 1,      # Single thread reduces peak memory
                    'num_gpu': 0,
                    'low_vram': True,
                }
            )
            
            # Extract response text - NO TIMEOUT, get complete response
            response_text = ""
            logger.info("Extracting response from LLM - no timeout, getting complete response...")
            
            if hasattr(response, '__aiter__'):
                # Streaming response - collect all chunks
                async for chunk in response:
                    if hasattr(chunk, 'response'):
                        response_text += chunk.response
                    elif isinstance(chunk, dict) and 'response' in chunk:
                        response_text += chunk['response']
                    
                    # Log progress for long responses
                    if len(response_text) % 500 == 0 and len(response_text) > 0:
                        logger.info(f"Response progress: {len(response_text)} characters generated...")
            else:
                # Non-streaming response
                if hasattr(response, 'response'):
                    response_text = response.response
                elif isinstance(response, dict) and 'response' in response:
                    response_text = response['response']
                else:
                    response_text = str(response)
            
            logger.info(f"LLM response extraction completed: {len(response_text)} characters")
            
            return response_text.strip()
            
        except Exception as e:
            logger.error(f"Error generating LLM response with Ollama: {e}")
            # Check if it's a memory error and try with smaller model or different approach
            if "memory" in str(e).lower() or "system memory" in str(e).lower():
                logger.info("Memory error detected, trying memory-efficient approach...")
                try:
                    return await self._generate_memory_efficient_response(prompt)
                except Exception as fallback_error:
                    logger.error(f"Memory-efficient generation also failed: {fallback_error}")
                    return "System memory constraints are preventing response generation. Please try with a shorter query."
            # Return a generic fallback response since we don't have query context here
            return "I'll provide a comprehensive answer using my knowledge and reasoning capabilities."
    
    async def _generate_memory_efficient_response(self, prompt: str) -> str:
        """
        Generate response with minimal memory usage by using smaller context
        
        Args:
            prompt: Input prompt
            
        Returns:
            Generated response
        """
        try:
            # Extract just the key information from the prompt (works for both RAG and KB prompts)
            lines = prompt.split('\n')
            question_line = ""
            key_content = []
            
            for line in lines:
                # Capture question line variants
                if line.startswith("Question:") or line.startswith("QUESTION:") or line.startswith("USER QUESTION:"):
                    question_line = line
            
            # Extract up to 2 short CONTENT blocks
            try:
                contents = re.findall(r"CONTENT:\n([\s\S]*?)(?:\n\n=== END SOURCE|$)", prompt)
                for c in contents[:2]:
                    snippet = c.strip()
                    if len(snippet) > 300:
                        snippet = snippet[:300] + "..."
                    if snippet:
                        key_content.append(snippet)
            except Exception:
                pass
            
            # Create minimal prompt
            minimal_prompt = f"""Answer this question using ONLY the Key Information below.
{question_line if question_line else ''}

Key Information:
{chr(10).join('- ' + k for k in key_content) if key_content else '(no key info extracted)'}

Provide a brief, factual answer in 4-6 sentences:"""
            
            logger.info(f"Using minimal prompt (length: {len(minimal_prompt)} chars)")
            
            # Try with conservative settings - NO TIMEOUT
            logger.info("Starting memory-efficient LLM generation - no timeout...")
            response = await self.llm_client.generate(
                model=self.llm_model_name,
                prompt=minimal_prompt,
                options={
                    'temperature': 0.3,
                    'num_predict': 200,   # Further reduced for reliability
                    'num_ctx': 768,       # Smaller context for memory safety
                    'num_batch': 1,
                    'num_thread': 1,
                    'num_gpu': 0,
                    'low_vram': True,
                }
            )
            
            # Extract response
            response_text = ""
            if hasattr(response, '__aiter__'):
                async for chunk in response:
                    if hasattr(chunk, 'response'):
                        response_text += chunk.response
                    elif isinstance(chunk, dict) and 'response' in chunk:
                        response_text += chunk['response']
            else:
                if hasattr(response, 'response'):
                    response_text = response.response
                elif isinstance(response, dict) and 'response' in response:
                    response_text = response['response']
                else:
                    response_text = str(response)
            
            return response_text.strip() if response_text.strip() else "Memory constraints prevented full response generation."
            
        except Exception as e:
            logger.error(f"Memory-efficient generation also failed: {e}")
            return "System memory constraints are preventing response generation. Please try with a smaller query or restart the system."
    
    async def _generate_with_chatgpt(self, query: str, scraped_data: List[Dict[str, Any]]) -> str:
        if not self.openai_api_key:
            return ""
        if not scraped_data:
            return ""
        try:
            if self.openai_client is None:
                self.openai_client = AsyncOpenAI(api_key=self.openai_api_key)
            sources = []
            for i, article in enumerate(scraped_data[:5], 1):
                title = article.get("title", "No Title")
                content = (article.get("content") or "").strip()
                if not content:
                    continue
                if len(content) > 1500:
                    content = content[:1500] + "..."
                url = article.get("url", "")
                sources.append(f"Source {i} - {title}\nURL: {url}\nContent:\n{content}")
            if not sources:
                return ""
            sources_text = "\n\n".join(sources)
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are an expert assistant. Read the web sources carefully and produce detailed summaries. "
                        "For each source, write a short paragraph of 3-4 full sentences summarizing the main points relevant to the user's question. "
                        "Then provide an overall synthesis that combines information from all sources. Do not just repeat headlines or list URLs."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "User question:\n"
                        f"{query}\n\n"
                        "Web sources (S1, S2, ... in the same order as below):\n"
                        f"{sources_text}\n\n"
                        "Output format:\n"
                        "For each source Si (in order):\n"
                        "- Start with 'Si:' followed by the article title.\n"
                        "- Then write 3-4 full sentences summarizing what this source says about the question.\n"
                        "After all sources, add 'Overall summary:' with 3-4 sentences synthesizing the main answer to the question across all sources.\n"
                        "Avoid outputs that only contain titles, headlines, or raw snippets without explanation."
                    ),
                },
            ]
            response = await self.openai_client.chat.completions.create(
                model=self.openai_model_name,
                messages=messages,
                temperature=0.4,
                max_tokens=1200,
            )
            choice = None
            if hasattr(response, "choices"):
                if response.choices:
                    choice = response.choices[0]
            elif isinstance(response, dict):
                choices = response.get("choices") or []
                if choices:
                    choice = choices[0]
            if choice is None:
                return ""
            content_obj = getattr(choice, "message", None)
            if isinstance(content_obj, dict):
                text = content_obj.get("content", "")
            else:
                text = getattr(content_obj, "content", "")
            return (text or "").strip()
        except Exception:
            logger.error("Error generating response from scraped data.")
            return ""
    
    async def _rag_generate(self, query: str, documents: List[Dict[str, Any]]) -> str:
        """
        Generate response using RAG pipeline
        
        Args:
            query: User query
            documents: Retrieved documents
            
        Returns:
            Generated response
        """
        try:
            # Store retrieved documents for fallback use
            self._last_retrieved_docs = documents
            
            # Create RAG prompt with context
            prompt = ResponsePrompts.get_rag_prompt(query, documents)
            
            # Generate response
            response = await self._generate_with_llm(prompt)
            
            # Check if response indicates memory constraints
            if "memory constraints" in response.lower() or "system memory" in response.lower():
                logger.info("LLM returned memory constraint message, using direct document response...")
                return self._generate_direct_response_from_docs(query, documents)
            
            return response
            
        except Exception as e:
            logger.error(f"Error in RAG generation: {e}")
            # Check if it's a memory error and use fallback
            if "memory" in str(e).lower() or "system memory" in str(e).lower():
                logger.info("LLM memory error in RAG, using direct document response...")
                return self._generate_direct_response_from_docs(query, documents)
            return ErrorPrompts.RESPONSE_ERROR
    
    def _generate_direct_response_from_docs(self, query: str, documents: List[Dict[str, Any]]) -> str:
        """
        Generate direct response from documents without LLM
        
        Args:
            query: User query
            documents: Retrieved documents
            
        Returns:
            Direct response from documents
        """
        if not documents:
            return "No relevant information found in the scraped data."
        
        # Use heuristic multi-article summary for a more coherent answer
        return self._heuristic_summary_from_docs(query, documents)
    
    async def _generate_with_rag_workflow(self, query: str, scraped_data: List[Dict[str, Any]]) -> str:
        """
        Generate response using RAG workflow with embeddings and FAISS
        
        Args:
            query: User query
            scraped_data: Scraped articles to use as knowledge base
            
        Returns:
            Generated response
        """
        try:
            logger.info("Starting RAG workflow...")
            
            # Step 1: Initialize embedding model if needed
            if self.embedding_model is None:
                logger.info("Initializing embedding model...")
                await self._load_embedding_model()
            
            # Step 2: Initialize FAISS index if needed
            if self.faiss_index is None:
                logger.info("Initializing FAISS index...")
                await self._initialize_faiss_index()
            
            # Step 3: Clear previous index and add new documents
            logger.info("Clearing previous index...")
            await self.clear_index()
            
            # Step 4: Add scraped documents to FAISS index with embeddings
            logger.info(f"Adding {len(scraped_data)} documents to FAISS index...")
            await self._add_documents_to_index(scraped_data)
            
            # Step 5: Retrieve relevant documents using vector search
            logger.info("Retrieving relevant documents using vector search...")
            relevant_docs = await self._retrieve_relevant_documents(query, k=3)
            
            if not relevant_docs:
                logger.warning("No relevant documents retrieved, falling back to knowledge base method")
                return await self._generate_with_knowledge_base(query, scraped_data)
            
            logger.info(f"Retrieved {len(relevant_docs)} relevant documents")
            
            # Step 6: Generate response using RAG
            logger.info("Generating response using RAG...")
            response = await self._rag_generate(query, relevant_docs)
            
            return response
            
        except Exception as e:
            logger.error(f"Error in RAG workflow: {e}")
            # Fallback to original knowledge base method
            logger.info("Falling back to knowledge base method...")
            return await self._generate_with_knowledge_base(query, scraped_data)
    
    async def _generate_with_knowledge_base(self, query: str, scraped_data: List[Dict[str, Any]]) -> str:
        """
        Generate response using scraped data as knowledge base
        
        Args:
            query: User query
            scraped_data: Scraped articles to use as knowledge base
            
        Returns:
            Generated response
        """
        try:
            # Create knowledge base prompt with scraped data
            prompt = self._create_knowledge_base_prompt(query, scraped_data)
            
            # Log prompt details for debugging
            logger.info(f"Knowledge base prompt length: {len(prompt)} chars")
            logger.info(f"Prompt preview: {prompt[:200]}...")
            
            # Generate response
            response = await self._generate_with_llm(prompt)
            
            # If LLM signals memory issues, fall back to direct document summary
            if response and ("memory constraints" in response.lower() or "system memory" in response.lower()):
                logger.info("KB generation hit memory constraints, using direct document fallback")
                # Limit to top 3 docs for stability
                docs = scraped_data[:3] if scraped_data else []
                return self._generate_direct_response_from_docs(query, docs)
            
            return response
            
        except Exception as e:
            logger.error(f"Error in knowledge base generation: {e}")
            return self._generate_fallback_response(query)
    
    def _create_knowledge_base_prompt(self, query: str, scraped_data: List[Dict[str, Any]]) -> str:
        """
        Create prompt using scraped data as knowledge base
        
        Args:
            query: User query
            scraped_data: Scraped articles
            
        Returns:
            Formatted prompt with knowledge base
        """
        # Prepare knowledge base content with better formatting
        knowledge_content = []
        valid_articles = 0
        
        for i, article in enumerate(scraped_data, 1):
            title = article.get('title', 'Unknown Title')
            content = article.get('content', '').strip()
            url = article.get('url', '')
            domain = article.get('domain', '')
            
            # Skip articles with no meaningful content
            if not content or len(content) < 50:
                continue
                
            valid_articles += 1
            
            # Use more content but still limit for memory efficiency
            if len(content) > 900:
                content = content[:900] + "..."
            
            # Better formatting with clear separation
            knowledge_content.append(f"""=== SOURCE {valid_articles} ===
Title: {title}
Domain: {domain}
URL: {url}

CONTENT:
{content}

=== END SOURCE {valid_articles} ===
""")
            
            # Hard cap on number of sources to keep prompt small
            if valid_articles >= 3:
                break
        
        knowledge_text = "\n".join(knowledge_content)
        
        # If no valid content, return a fallback prompt
        if valid_articles == 0:
            return f"""You are an expert assistant. The user asked: "{query}"

Unfortunately, the web search did not return articles with sufficient content to answer this question. Please provide a helpful response based on your knowledge, clearly stating that you're using general knowledge since recent web sources were not available.

Answer:"""
        
        # MANDATORY prompt - LLM MUST use scraped data
        return f"""You are an expert assistant. You MUST answer the user's question using ONLY the provided web sources below.

MANDATORY REQUIREMENTS:
1. Use the information from the {valid_articles} web sources provided below
2. Do NOT list headlines; produce a synthesized summary that explains the answer
3. Extract specific facts, figures, and examples from the sources
4. Synthesize information from multiple sources to create a comprehensive answer
5. Reference specific sources when providing information (e.g., [S1], [S2])
6. If sources are partial, combine them constructively to answer the question

WEB SOURCES (YOU MUST USE THESE):
{knowledge_text}

USER QUESTION: {query}

MANDATORY RESPONSE FORMAT:
- Begin with: "Based on the web sources provided:"
- Provide a concise synthesis (not a list of links/headlines)
- Use a short, structured outline with bullet points and sub-bullets
- Include citations inline like [S1], [S2] that map to the source numbers above
- End with 2-3 sentence summary of the key takeaways

You MUST provide an answer using the sources above.

Answer:"""

    async def _direct_generate(self, query: str) -> str:
        """
        Generate direct response without context
        
        Args:
            query: User query
            
        Returns:
            Generated response
        """
        try:
            # Create direct prompt
            prompt = ResponsePrompts.get_direct_prompt(query)
            
            # Generate response
            response = await self._generate_with_llm(prompt)
            
            return response
            
        except Exception as e:
            logger.error(f"Error in direct generation: {e}")
            return self._generate_fallback_response(query)
    
    async def generate_response_with_scraped_data(self, query: str, keywords: List[str], 
                                                 scraped_data: List[Dict[str, Any]]) -> str:
        """
        Generate response directly using provided scraped data (streamlined workflow)
        
        Args:
            query: User query
            keywords: Extracted keywords
            scraped_data: Scraped articles from web search
            
        Returns:
            Generated response
        """
        try:
            logger.info(f"Generating response for query: {query[:100]}...")
            logger.info(f"Scraped data available: {len(scraped_data) if scraped_data else 0} articles")
            
            # Log scraped data details for debugging
            if scraped_data:
                for i, article in enumerate(scraped_data[:3]):  # Log first 3 articles
                    content_length = len(article.get('content', ''))
                    content_preview = article.get('content', '')[:100].replace('\n', ' ') if article.get('content') else 'No content'
                    logger.info(f"Article {i+1}: {article.get('title', 'No title')[:50]}... (content: {content_length} chars)")
                    logger.info(f"  Content preview: {content_preview}...")
            
            # Validate query
            if not validate_query(query):
                return "Please provide a valid question."
            
            # # ALWAYS prioritize scraped data - use RAG workflow for better responses
            # response = ""
            # try:
            #     if scraped_data and len(scraped_data) > 0:
            #         # Be more lenient - accept articles with at least 50 characters or use all available
            #         valid_articles = [art for art in scraped_data if len(art.get('content', '').strip()) > 50]
            #         
            #         # If no articles meet the 50 char requirement, use all available articles
            #         if not valid_articles:
            #             valid_articles = scraped_data
            #             logger.info(f"Using ALL {len(scraped_data)} articles with RAG workflow (relaxed content requirements)")
            #         else:
            #             logger.info(f"Using {len(valid_articles)} valid articles (out of {len(scraped_data)}) with RAG workflow")
            #         
            #         # Use RAG workflow for better response generation
            #         response = await self._generate_with_rag_workflow(query, valid_articles)
            #         logger.info(f"Generated response using RAG workflow: {len(response)} characters")
            #     else:
            #         logger.warning("No scraped data available, using direct generation")
            #         response = await self._direct_generate(query)
            # except Exception as llm_error:
            #     logger.error(f"LLM generation failed: {llm_error}")
            #     # Fall back to knowledge-base prompt (LLM summarization) instead of listing headlines
            #     kb_articles = valid_articles if 'valid_articles' in locals() else scraped_data
            #     response = await self._generate_with_knowledge_base(query, kb_articles)
            # 
            # # If response is too generic, use fallback with scraped data
            # generic_msg = "I'll provide a comprehensive answer using my knowledge and reasoning capabilities."
            # if response.strip() == generic_msg:
            #     logger.info("Response too generic, retrying with knowledge base prompt")
            #     response = await self._generate_with_knowledge_base(query, scraped_data or [])
            #     if response.strip() == generic_msg:
            #         logger.info("Knowledge base prompt still generic, using document-based fallback")
            #         response = self._generate_fallback_response(query, scraped_data)
            #
            # # If memory constraint message leaked through, synthesize heuristically from docs
            # if "system memory constraints" in response.lower():
            #     logger.info("Detected memory constraint message in final response, using heuristic summary")
            #     response = self._heuristic_summary_from_docs(query, scraped_data or [])
            # 
            # # Post-process response
            # response = self._post_process_response(response, keywords)
            # 
            # logger.info(f"Final response generated successfully (length: {len(response)} chars)")
            # return response

            response = ""
            use_local_llm = False

            if self.openai_api_key and scraped_data and len(scraped_data) > 0:
                response = await self._generate_with_chatgpt(query, scraped_data)
                # If the external summarizer fails or returns a very short / low-content answer,
                # fall back to the local LLM + document-based summarization pipeline.
                if not response or len(response) < 400:
                    use_local_llm = True
                    response = ""
            else:
                use_local_llm = True

            if use_local_llm:
                try:
                    if scraped_data and len(scraped_data) > 0:
                        valid_articles = [art for art in scraped_data if len(art.get('content', '').strip()) > 50]
                        if not valid_articles:
                            valid_articles = scraped_data
                            logger.info(f"Using ALL {len(scraped_data)} articles with RAG workflow (relaxed content requirements)")
                        else:
                            logger.info(f"Using {len(valid_articles)} valid articles (out of {len(scraped_data)}) with RAG workflow")
                        response = await self._generate_with_rag_workflow(query, valid_articles)
                        logger.info(f"Generated response using RAG workflow: {len(response)} characters")
                    else:
                        logger.warning("No scraped data available, using direct generation")
                        response = await self._direct_generate(query)
                except Exception as llm_error:
                    logger.error(f"LLM generation failed: {llm_error}")
                    kb_articles = valid_articles if 'valid_articles' in locals() else scraped_data
                    response = await self._generate_with_knowledge_base(query, kb_articles)

                generic_msg = "I'll provide a comprehensive answer using my knowledge and reasoning capabilities."
                if response.strip() == generic_msg:
                    logger.info("Response too generic, retrying with knowledge base prompt")
                    response = await self._generate_with_knowledge_base(query, scraped_data or [])
                    if response.strip() == generic_msg:
                        logger.info("Knowledge base prompt still generic, using document-based fallback")
                        response = self._generate_fallback_response(query, scraped_data)

                if "system memory constraints" in response.lower():
                    logger.info("Detected memory constraint message in final response, using heuristic summary")
                    response = self._heuristic_summary_from_docs(query, scraped_data or [])

            response = self._post_process_response(response, keywords)
            
            logger.info(f"Final response generated successfully (length: {len(response)} chars)")
            return response
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            # Always return a proper response, never an error message
            return self._generate_fallback_response(query)
    
    async def generate_response(self, query: str, keywords: List[str], 
                               scraped_data: List[Dict[str, Any]] = None) -> str:
        """
        Generate contextual response using scraped data as knowledge base (legacy method)
        
        Args:
            query: User query
            keywords: Extracted keywords
            scraped_data: Scraped articles (optional, will use fallback if not provided)
            
        Returns:
            Generated response
        """
        try:
            logger.info(f"Generating response for query: {query[:100]}...")
            
            # Validate query
            if not validate_query(query):
                return "Please provide a valid question."
            
            # Use provided scraped data with RAG workflow
            if scraped_data and len(scraped_data) > 0:
                logger.info(f"Using {len(scraped_data)} scraped articles with RAG workflow")
                response = await self._generate_with_rag_workflow(query, scraped_data)
            else:
                # Use fallback response if no scraped data provided
                logger.info("No scraped data provided, using fallback response")
                response = self._generate_fallback_response(query)
            
            # Post-process response
            response = self._post_process_response(response, keywords)
            
            logger.info("Response generated successfully")
            return response
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return f"{ErrorPrompts.RESPONSE_ERROR}\n\nTechnical details: {str(e)}"
    
    async def _auto_load_scraped_data(self, query: str, keywords: List[str]) -> List[Dict[str, Any]]:
        """
        Automatically load scraped data for the query
        
        Args:
            query: User query
            keywords: Extracted keywords
            
        Returns:
            List of scraped articles
        """
        try:
            from .utils import get_latest_scraped_file, load_scraped_data
            
            # Try to find the most recent scraped file
            latest_file = get_latest_scraped_file()
            
            if latest_file:
                logger.info(f"Auto-loading scraped data from: {latest_file}")
                scraped_data = load_scraped_data(latest_file)
                
                if scraped_data and 'articles' in scraped_data:
                    articles = scraped_data['articles']
                    logger.info(f"Auto-loaded {len(articles)} articles")
                    return articles
            
            logger.info("No scraped data files found for auto-loading")
            return []
            
        except Exception as e:
            logger.error(f"Error auto-loading scraped data: {e}")
            return []
    
    def _create_basic_response_from_scraped_data(self, query: str, scraped_data: List[Dict[str, Any]]) -> str:
        """
        Create a basic response using scraped data when LLM fails
        
        Args:
            query: User query
            scraped_data: Scraped articles
            
        Returns:
            Basic response using scraped content
        """
        try:
            response_parts = [
                f"**Response to: {query}**\n",
                "Based on recent web sources, here's what I found:\n"
            ]
            
            for i, article in enumerate(scraped_data[:3], 1):  # Use top 3 articles
                title = article.get('title', 'Unknown Title')
                content = article.get('content', '')
                url = article.get('url', '')
                
                # Extract key sentences from content
                sentences = content.split('. ')
                key_sentences = [s.strip() + '.' for s in sentences[:3] if len(s.strip()) > 20]
                
                response_parts.append(f"\n**Source {i}: {title}**")
                if key_sentences:
                    response_parts.append("Key points:")
                    for sentence in key_sentences:
                        response_parts.append(f"- {sentence}")
                
                if url:
                    response_parts.append(f"Source: {url}")
            
            response_parts.append("\n**Note:** This response was generated using web content due to system memory constraints.")
            
            return "\n".join(response_parts)
            
        except Exception as e:
            logger.error(f"Error creating basic response from scraped data: {e}")
            return f"Found {len(scraped_data)} relevant articles but couldn't process them due to system constraints."

    def _heuristic_summary_from_docs(self, query: str, documents: List[Dict[str, Any]]) -> str:
        """Create a concise summary from docs without using the LLM (memory-safe).
        Picks top sentences matching query keywords across sources and adds simple citations.
        """
        if not documents:
            return "Based on available information, no sufficient content was retrieved to answer the question. Please try a more specific query."
        
        # Build keyword set
        query_words = [w.lower() for w in re.split(r"\W+", query) if len(w) > 2]
        kw_set = set(query_words)
        
        # Score sentences
        candidates = []  # (score, sentence, source_idx, title)
        for i, doc in enumerate(documents[:5], 1):
            title = doc.get('title', f'Source {i}')
            url = doc.get('url', '')
            content = doc.get('content', '')
            if not content:
                continue
            # Split into sentences
            sentences = re.split(r"(?<=[\.!?])\s+", content)
            for sent in sentences:
                s = sent.strip()
                if len(s) < 40:
                    continue
                tokens = [t.lower() for t in re.split(r"\W+", s) if t]
                if not tokens:
                    continue
                # Score by keyword overlap + position bias
                overlap = sum(1 for t in tokens if t in kw_set)
                score = overlap + (1.0 if len(candidates) < 5 else 0.0)
                if overlap > 0:
                    candidates.append((score, s, i, title, url))
        
        # Pick top 6 sentences from diverse sources
        candidates.sort(key=lambda x: x[0], reverse=True)
        picked = []
        used_sents = set()
        per_source_count = {}
        for score, s, idx, title, url in candidates:
            if len(picked) >= 6:
                break
            if s in used_sents:
                continue
            per_source_count[idx] = per_source_count.get(idx, 0) + 1
            if per_source_count[idx] > 2:
                continue
            used_sents.add(s)
            picked.append((s, idx, title, url))
        
        # Format response
        parts = ["Based on the web sources provided:",""]
        if not picked:
            # Fall back to titles with note
            for i, doc in enumerate(documents[:3], 1):
                t = doc.get('title', f'Source {i}')
                parts.append(f"- {t} [S{i}]")
        else:
            for s, idx, title, url in picked:
                parts.append(f"- {s} [S{idx}]")
        
        # Add simple source mapping
        parts.append("")
        parts.append("Sources:")
        for i, doc in enumerate(documents[:5], 1):
            t = doc.get('title', f'Source {i}')
            u = doc.get('url', '')
            parts.append(f"[S{i}] {t} - {u}")
        
        return "\n".join(parts)
    
    def _generate_fallback_response(self, query: str, scraped_data: List[Dict[str, Any]] = None) -> str:
        """
        Generate a fallback response when LLM fails, using scraped data if available
        
        Args:
            query: User query
            scraped_data: Scraped articles to use for response
            
        Returns:
            Fallback response
        """
        # If we have scraped data, use it to create a basic response
        if scraped_data and len(scraped_data) > 0:
            return self._generate_direct_response_from_docs(query, scraped_data)
        
        # Simple keyword-based responses for common queries
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['ai', 'artificial intelligence', 'machine learning']):
            return """**Response:**

Artificial Intelligence (AI) is a branch of computer science that focuses on creating systems capable of performing tasks that typically require human intelligence. Here are the key aspects:

**Core Concepts:**
- **Machine Learning**: AI systems that learn from data without explicit programming
- **Neural Networks**: Computing systems inspired by biological neural networks
- **Deep Learning**: Advanced machine learning using multi-layered neural networks
- **Natural Language Processing**: AI's ability to understand and generate human language

**Applications:**
- Healthcare: Medical diagnosis, drug discovery, personalized treatment
- Transportation: Autonomous vehicles, traffic optimization
- Business: Customer service, data analysis, process automation
- Technology: Search engines, recommendation systems, virtual assistants

**Benefits:**
- Increased efficiency and productivity
- Enhanced decision-making capabilities
- Automation of repetitive tasks
- Improved accuracy in complex calculations
- 24/7 availability for critical systems

AI continues to evolve rapidly, transforming industries and creating new possibilities for solving complex problems across various domains."""

        elif any(word in query_lower for word in ['healthcare', 'health', 'medical']):
            return """**Response:**

Healthcare is a critical sector that encompasses the prevention, diagnosis, treatment, and management of diseases and medical conditions. Here's a comprehensive overview:

**Key Areas:**
- **Preventive Care**: Regular check-ups, vaccinations, health screenings
- **Diagnostic Services**: Medical imaging, laboratory tests, clinical assessments
- **Treatment Options**: Medications, surgeries, therapies, rehabilitation
- **Public Health**: Disease prevention, health education, community wellness

**Modern Healthcare Trends:**
- **Digital Health**: Telemedicine, electronic health records, mobile health apps
- **Precision Medicine**: Personalized treatments based on genetic profiles
- **AI Integration**: Diagnostic assistance, drug discovery, treatment optimization
- **Preventive Focus**: Early detection and lifestyle-based interventions

**Benefits of Good Healthcare:**
- Improved quality of life and life expectancy
- Reduced healthcare costs through prevention
- Better management of chronic conditions
- Enhanced patient outcomes and satisfaction
- Economic benefits through a healthier workforce

Access to quality healthcare is essential for individual well-being and societal progress."""

        elif any(word in query_lower for word in ['exercise', 'fitness', 'physical activity']):
            return """**Response:**

Exercise and physical activity are fundamental components of a healthy lifestyle with numerous benefits for both physical and mental well-being.

**Physical Benefits:**
- **Cardiovascular Health**: Strengthens heart and improves circulation
- **Muscle Strength**: Builds and maintains muscle mass and bone density
- **Weight Management**: Helps maintain healthy body weight
- **Immune System**: Boosts immune function and disease resistance
- **Energy Levels**: Increases overall energy and stamina

**Mental Health Benefits:**
- **Stress Reduction**: Releases endorphins that improve mood
- **Better Sleep**: Promotes deeper, more restful sleep
- **Cognitive Function**: Enhances memory and mental clarity
- **Anxiety Relief**: Reduces symptoms of anxiety and depression
- **Self-Confidence**: Improves body image and self-esteem

**Types of Exercise:**
- **Aerobic**: Running, swimming, cycling, dancing
- **Strength Training**: Weightlifting, resistance exercises
- **Flexibility**: Yoga, stretching, Pilates
- **Balance**: Tai chi, balance exercises

**Recommendations:**
- At least 150 minutes of moderate-intensity exercise per week
- Include both aerobic and strength training activities
- Start gradually and increase intensity over time
- Find activities you enjoy to maintain consistency

Regular exercise is one of the most effective ways to improve overall health and quality of life."""

        elif any(word in query_lower for word in ['russia', 'ukraine', 'conflict', 'war', 'military', 'diplomatic']):
            return """**Response:**

The Russia-Ukraine conflict is an ongoing geopolitical crisis that began in 2014 and escalated significantly in February 2022. Here's a comprehensive overview of the current situation:

**Current Military Situation:**
- **Territorial Control**: Russia currently occupies significant portions of eastern and southern Ukraine
- **Frontline Dynamics**: Active fighting continues along multiple fronts with varying intensity
- **Military Operations**: Both sides have conducted offensive and defensive operations throughout 2024
- **Casualties**: The conflict has resulted in significant military and civilian casualties on both sides

**Recent Diplomatic Developments:**
- **International Support**: Ukraine continues to receive military and humanitarian aid from Western allies
- **Sanctions**: Comprehensive economic sanctions remain in place against Russia
- **Peace Negotiations**: Various diplomatic initiatives have been attempted, though no lasting peace agreement has been reached
- **International Organizations**: UN, EU, and other organizations continue to monitor and respond to the situation

**Key Issues:**
- **Territorial Integrity**: Ukraine's sovereignty and territorial integrity remain central concerns
- **Humanitarian Crisis**: Millions of refugees and internally displaced persons
- **Economic Impact**: Global economic effects including energy and food security concerns
- **Nuclear Safety**: Concerns about nuclear facilities and potential escalation

**International Response:**
- **Military Aid**: Continued provision of weapons, training, and intelligence support to Ukraine
- **Economic Measures**: Ongoing sanctions and economic pressure on Russia
- **Diplomatic Efforts**: Multilateral diplomatic initiatives to find a peaceful resolution
- **Legal Actions**: International legal proceedings and investigations

The situation remains fluid and complex, with ongoing developments in both military and diplomatic spheres. For the most current information, it's important to consult recent news sources and official statements from involved parties."""

        elif any(word in query_lower for word in ['quantum', 'computing', 'quantum computing']):
            return """**Response:**

Quantum computing represents a revolutionary approach to computation that leverages the principles of quantum mechanics to process information in fundamentally new ways. Here's a comprehensive overview:

**Core Concepts:**
- **Quantum Bits (Qubits)**: Unlike classical bits that are either 0 or 1, qubits can exist in superposition states
- **Superposition**: Qubits can be in multiple states simultaneously, enabling parallel processing
- **Entanglement**: Qubits can be correlated in ways that classical bits cannot, enabling quantum algorithms
- **Quantum Interference**: Quantum states can interfere constructively or destructively

**Recent Developments:**
- **Hardware Advances**: Progress in quantum processor design and error correction
- **Algorithm Development**: New quantum algorithms for optimization, cryptography, and simulation
- **Commercial Applications**: Companies like IBM, Google, and Microsoft offering quantum cloud services
- **Research Breakthroughs**: Advances in quantum error correction and fault-tolerant quantum computing

**Key Applications:**
- **Cryptography**: Quantum computers could break current encryption methods, driving quantum-safe cryptography
- **Optimization**: Solving complex optimization problems in logistics, finance, and drug discovery
- **Simulation**: Modeling quantum systems for materials science, chemistry, and physics
- **Machine Learning**: Quantum machine learning algorithms for pattern recognition

**Current Challenges:**
- **Error Rates**: Quantum systems are highly sensitive to environmental noise
- **Scalability**: Building large-scale quantum computers with many qubits
- **Coherence Time**: Maintaining quantum states long enough for computation
- **Cost and Complexity**: Quantum computers require extreme cooling and isolation

**Major Players:**
- **IBM**: IBM Quantum Network and Qiskit platform
- **Google**: Quantum AI lab and Sycamore processor
- **Microsoft**: Azure Quantum platform and Q# programming language
- **IonQ**: Trapped ion quantum computers
- **Rigetti**: Quantum cloud computing services

**Future Outlook:**
Quantum computing is still in its early stages, but rapid progress suggests it could revolutionize fields from cryptography to drug discovery within the next decade. The technology promises to solve problems that are intractable for classical computers."""

        else:
            return f"""**Response:**

Thank you for your question about "{query}". While I'm experiencing some technical limitations with my advanced language processing capabilities, I can provide you with general information on this topic.

**General Approach:**
- This appears to be a question that would benefit from comprehensive research and analysis
- The topic involves multiple aspects that could be explored in detail
- There are likely recent developments and current information available
- Professional expertise and reliable sources would provide the most accurate information

**Recommendations:**
- Consult authoritative sources and recent publications
- Look for expert opinions and peer-reviewed research
- Consider multiple perspectives on the topic
- Verify information from reliable, up-to-date sources

I apologize for not being able to provide a more detailed response at this time. For the most comprehensive and current information, I'd recommend consulting specialized resources or experts in the relevant field."""

    def _post_process_response(self, response: str, keywords: List[str]) -> str:
        """
        Post-process the generated response
        
        Args:
            response: Generated response
            keywords: Query keywords
            
        Returns:
            Post-processed response
        """
        try:
            # Clean response
            response = clean_text(response, max_length=4000)
            
            # Remove common refusal patterns and replace with helpful responses
            refusal_patterns = [
                "I cannot answer",
                "I don't have information",
                "the knowledge base does not contain",
                "I'm sorry, I cannot",
                "I'm unable to",
                "I don't have access to",
                "I cannot provide",
                "I don't have enough information",
                "I cannot tell you",
                "I don't know",
                "I'm not able to",
                "I cannot help",
                "I don't have the information",
                "I cannot find",
                "I don't have data",
                "I cannot access",
                "I don't have access",
                "I cannot retrieve",
                "I don't have details",
                "I cannot locate"
            ]
            
            # Check if response contains refusal patterns
            response_lower = response.lower()
            has_refusal = any(pattern.lower() in response_lower for pattern in refusal_patterns)
            
            if has_refusal:
                # Replace refusal with helpful response
                response = f"Based on my knowledge and reasoning, here's what I can tell you about this topic:\n\n{response}"
            
            # Add general context if needed
            if not response.startswith("**") and not response.startswith("Based on"):
                response = f"**Response:**\n\n{response}"
            
            # Ensure response ends properly
            if not response.endswith(('.', '!', '?')):
                response += "."
            
            return response
            
        except Exception as e:
            logger.error(f"Error post-processing response: {e}")
            return response
    
    async def clear_index(self):
        """Clear the FAISS index and document store"""
        try:
            self.faiss_index = None
            self.document_store = {}
            
            # Remove files
            index_path = "data/embeddings/faiss_index.bin"
            docs_path = "data/embeddings/document_store.json"
            
            if os.path.exists(index_path):
                os.remove(index_path)
            if os.path.exists(docs_path):
                os.remove(docs_path)
            
            logger.info("Index cleared successfully")
            
        except Exception as e:
            logger.error(f"Error clearing index: {e}")
    
    def get_index_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the current index
        
        Returns:
            Index statistics
        """
        try:
            stats = {
                'total_vectors': 0,
                'total_documents': len(self.document_store),
                'index_loaded': self.faiss_index is not None,
                'embedding_model': self.embedding_model_name,
                'llm_model': self.llm_model_name
            }
            
            if self.faiss_index is not None:
                stats['total_vectors'] = self.faiss_index.ntotal
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting index stats: {e}")
            return {'error': str(e)}

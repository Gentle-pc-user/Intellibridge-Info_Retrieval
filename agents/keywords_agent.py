"""
KeywordsGeneratorAgent for keyword extraction from user queries
Uses Ollama Gemma 3 model to extract relevant keywords for web search
"""

import asyncio
import json
import logging
import re
from typing import Dict, List, Optional

import ollama

from .utils import setup_logging

logger = setup_logging()

class KeywordsPrompts:
    """Prompts for the KeywordsGeneratorAgent"""
    
    @staticmethod
    def get_keywords_prompt(query: str) -> str:
        """Generate keywords extraction prompt for a given query"""
        return f"""You are an intelligent keyword extractor. Analyze the user's query and extract the most relevant keywords that would be useful for web search to find CURRENT, UP-TO-DATE information.

Your task is to:
1. Identify the main concepts and topics in the query
2. Extract 3-8 relevant keywords that would help find RECENT and CURRENT information
3. Focus on specific terms, proper nouns, and key concepts
4. For questions about "current" or "who is" - prioritize terms that will find the most recent information
5. Include temporal keywords like "current", "2024", "2025" when appropriate
6. Avoid common words like "what", "how", "the", "is", "elaborate", "explain" etc.
7. For political positions, avoid specific names unless certain they are current
8. Do NOT output generic words like "today", "todays", "latest", "news", "breaking", "updates"

**Output Format:**
Keywords: [keyword1, keyword2, keyword3, ...]

**Query to analyze:** {query}

**Special Instructions:**
- For "current prime minister" queries, use "current prime minister", "2024", "2025" rather than specific names
- For "latest" queries, include "latest", "recent", "2024", "2025"
- Prioritize keywords that will find the most recent information available"""

class KeywordsGeneratorAgent:
    """Agent responsible for keyword extraction from user queries"""
    
    def __init__(self, model_name: str = "llama3.2-vision", ollama_host: str = "http://localhost:11434"):
        """
        Initialize the KeywordsGeneratorAgent
        
        Args:
            model_name: Name of the Ollama model to use
            ollama_host: Ollama server URL
        """
        self.model_name = model_name
        self.ollama_host = ollama_host
        self.client = None
        
        logger.info(f"KeywordsGeneratorAgent initialized with Ollama model: {self.model_name}")
        
    async def _initialize_client(self):
        """Initialize the Ollama client"""
        if self.client is None:
            try:
                logger.info(f"Initializing Ollama client for model: {self.model_name}")
                
                # Initialize Ollama client
                self.client = ollama.AsyncClient(host=self.ollama_host)
                
                # Check if model is available
                try:
                    models = await self.client.list()
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
                    
                    if self.model_name not in model_names:
                        logger.warning(f"Model {self.model_name} not found. Available models: {model_names}")
                        logger.info(f"Attempting to pull model {self.model_name}...")
                        await self.client.pull(self.model_name)
                        logger.info(f"Successfully pulled model {self.model_name}")
                    else:
                        logger.info(f"Model {self.model_name} is available")
                        
                except Exception as e:
                    logger.error(f"Error checking/pulling model: {e}")
                    # Try to pull the model anyway
                    try:
                        logger.info(f"Attempting to pull model {self.model_name}...")
                        await self.client.pull(self.model_name)
                        logger.info(f"Successfully pulled model {self.model_name}")
                    except Exception as pull_error:
                        logger.error(f"Failed to pull model: {pull_error}")
                        raise
                
                logger.info("Ollama client initialized successfully")
                
            except Exception as e:
                logger.error(f"Failed to initialize Ollama client: {e}")
                raise
    
    async def _generate_response(self, prompt: str) -> str:
        """
        Generate response using the Ollama model
        
        Args:
            prompt: Input prompt
            
        Returns:
            Generated response text
        """
        await self._initialize_client()
        
        try:
            # Generate response using Ollama
            response = await self.client.generate(
                model=self.model_name,
                prompt=prompt,
                options={
                    'temperature': 0.3,
                    'top_p': 0.9,
                    'num_predict': 128,   # Reduced from max_tokens to num_predict
                    'num_ctx': 512,       # Context window
                    'num_batch': 1,       # Process one batch at a time
                    'num_thread': 2,      # Limit threads to reduce memory
                }
            )
            
            # Extract response text
            response_text = ""
            if hasattr(response, '__aiter__'):
                # Streaming response
                async for chunk in response:
                    if hasattr(chunk, 'response'):
                        response_text += chunk.response
                    elif isinstance(chunk, dict) and 'response' in chunk:
                        response_text += chunk['response']
            else:
                # Non-streaming response
                if hasattr(response, 'response'):
                    response_text = response.response
                elif isinstance(response, dict) and 'response' in response:
                    response_text = response['response']
                else:
                    response_text = str(response)
            
            return response_text.strip()
            
        except Exception as e:
            logger.error(f"Error generating response with Ollama: {e}")
            # Return fallback keywords based on query content
            return self._generate_fallback_keywords(query)
    
    def _generate_fallback_keywords(self, query: str) -> str:
        """
        Generate fallback keywords when LLM fails
        
        Args:
            query: User query
            
        Returns:
            Fallback keywords string
        """
        query_lower = query.lower()
        
        # Extract key terms based on query content
        keywords = []
        
        # AI/Tech related
        if any(word in query_lower for word in ['ai', 'artificial intelligence', 'machine learning', 'neural networks']):
            keywords.extend(['artificial intelligence', 'AI', 'machine learning', 'technology'])
        
        # Healthcare related
        if any(word in query_lower for word in ['healthcare', 'health', 'medical', 'medicine']):
            keywords.extend(['healthcare', 'medical', 'health', 'medicine'])
        
        # Russia-Ukraine related
        if any(word in query_lower for word in ['russia', 'ukraine', 'conflict', 'war', 'military', 'diplomatic']):
            keywords.extend(['Russia', 'Ukraine', 'conflict', 'military', 'diplomatic'])
        
        # Quantum computing related
        if any(word in query_lower for word in ['quantum', 'computing', 'quantum computing']):
            keywords.extend(['quantum computing', 'quantum', 'technology', 'computing'])
        
        # Geopolitics related
        if any(word in query_lower for word in ['geopolitics', 'international', 'foreign policy', 'diplomacy']):
            keywords.extend(['geopolitics', 'international relations', 'diplomacy'])
        
        # Exercise/Fitness related
        if any(word in query_lower for word in ['exercise', 'fitness', 'physical activity', 'workout']):
            keywords.extend(['exercise', 'fitness', 'physical activity', 'health'])
        
        # If no specific keywords found, extract general terms
        if not keywords:
            # Extract important words from the query
            words = query.split()
            important_words = [word.strip('.,!?') for word in words if len(word) > 3 and word.lower() not in ['what', 'are', 'the', 'latest', 'developments', 'tell', 'me', 'about']]
            keywords = important_words[:5]  # Take first 5 important words
        
        # Normalize and augment
        cleaned = self._clean_and_augment_keywords(keywords, query)
        return f"Keywords: {cleaned}"

    def _parse_keywords_result(self, response: str, original_query: str = "") -> Dict[str, any]:
        """
        Parse the model response to extract keywords
        
        Args:
            response: Raw model response
            original_query: Original user query for fallback
            
        Returns:
            Parsed keywords result
        """
        try:
            lines = response.strip().split('\n')
            keywords = []
            
            # Parse the structured output
            for line in lines:
                line = line.strip()
                if line.startswith('Keywords:'):
                    keywords_text = line.replace('Keywords:', '').strip()
                    # Parse keywords from the response
                    if keywords_text.startswith('[') and keywords_text.endswith(']'):
                        # Remove brackets and split by comma
                        keywords_text = keywords_text[1:-1]
                        keywords = [kw.strip().strip('"\'') for kw in keywords_text.split(',')]
                    else:
                        # Split by comma if not in brackets
                        keywords = [kw.strip().strip('"\'') for kw in keywords_text.split(',')]
                    break
            
            # Clean and validate
            keywords = self._clean_and_augment_keywords(keywords, original_query)
            
           
            if not keywords:
                keywords = self._extract_keywords_from_query(original_query)
            
            return {
                'keywords': keywords,
                'confidence': 0.9 if keywords else 0.5
            }
            
        except Exception as e:
            logger.error(f"Error parsing keywords result: {e}")
            # Fallback: extract keywords from original query
            keywords = self._extract_keywords_from_query(original_query)
            
            return {
                'keywords': keywords,
                'confidence': 0.6
            }
    
    def _extract_keywords_from_query(self, query: str) -> List[str]:
        """
        Extract keywords from query as fallback
        
        Args:
            query: User query
            
        Returns:
            List of keywords
        """
        if not query:
            return []
        
        # Simple keyword extraction - remove common words and split
        common_words = {'what', 'how', 'when', 'where', 'why', 'who', 'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'must'}
        
        # Split query into words and filter
        words = query.lower().replace(',', ' ').replace('.', ' ').replace('?', ' ').replace('!', ' ').split()
        banned = {'today', "today's", 'todays', 'latest', 'news', 'breaking', 'update', 'updates', 'recent'}
        keywords = [word for word in words if word not in common_words and word not in banned and len(word) > 2]
        
        # Ensure AI topic coverage when implied
        if any(t in words for t in ['ai', 'artificial', 'intelligence', 'ml', 'machine', 'gpt']):
            base = ['ai', 'artificial intelligence', 'machine learning']
            for b in base:
                if b not in keywords:
                    keywords.append(b)
        
        return keywords[:8]

    def _clean_and_augment_keywords(self, keywords: List[str], original_query: str) -> List[str]:
        if not keywords:
            return []
        cleaned = []
        seen = set()
        banned = {'today', "today's", 'todays', 'latest', 'news', 'breaking', 'update', 'updates', 'recent'}
        for kw in keywords:
            k = str(kw).strip().strip('"\'[](){}').lower()
            k = re.sub(r"\s+", ' ', k)
            if not k or k in banned:
                continue
            if k not in seen:
                seen.add(k)
                cleaned.append(k)
        if any(t in original_query.lower() for t in ['ai', 'artificial intelligence', 'machine learning']):
            for b in ['ai', 'artificial intelligence', 'machine learning']:
                if b not in cleaned:
                    cleaned.append(b)
        return cleaned[:8]
    
    async def extract_keywords(self, query: str) -> Dict[str, any]:
        """
        Extract keywords from user query
        
        Args:
            query: User query
            
        Returns:
            Dictionary with keywords and confidence
        """
        try:
            logger.info(f"Extracting keywords for query: {query[:100]}...")
            
            # Validate query
            if not query or not query.strip():
                return {
                    'keywords': [],
                    'confidence': 0.0
                }
            
            # Generate prompt
            prompt = KeywordsPrompts.get_keywords_prompt(query)
            
            # Generate response
            response = await self._generate_response(prompt)
            
            # Parse result
            result = self._parse_keywords_result(response, query)
            
            logger.info(f"Keywords extracted: {result['keywords']} (confidence: {result['confidence']:.2f})")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in keyword extraction: {e}")
            # Fallback: extract keywords from query
            keywords = self._extract_keywords_from_query(query)
            return {
                'keywords': keywords,
                'confidence': 0.7
            }
    
    async def extract_keywords_batch(self, queries: List[str]) -> List[Dict[str, any]]:
        """
        Extract keywords from multiple queries
        
        Args:
            queries: List of user queries
            
        Returns:
            List of keyword extraction results
        """
        results = []
        
        for query in queries:
            try:
                result = await self.extract_keywords(query)
                results.append(result)
            except Exception as e:
                logger.error(f"Error processing query '{query}': {e}")
                results.append({
                    'keywords': self._extract_keywords_from_query(query),
                    'confidence': 0.7
                })
        
        return results

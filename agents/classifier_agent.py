"""
KeywordsGeneratorAgent for keyword extraction from user queries
Uses Ollama Gemma 3 model to extract relevant keywords for web search
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional

import ollama

from .utils import setup_logging

logger = setup_logging()

class KeywordsPrompts:
    """Prompts for the KeywordsGeneratorAgent"""
    
    @staticmethod
    def get_keywords_prompt(query: str) -> str:
        """Generate keywords extraction prompt for a given query"""
        return f"""You are an intelligent keyword extractor. Analyze the user's query and extract the most relevant keywords that would be useful for web search.

Your task is to:
1. Identify the main concepts and topics in the query
2. Extract 3-8 relevant keywords that would help find related information
3. Focus on specific terms, proper nouns, and key concepts
4. Avoid common words like "what", "how", "the", "is", etc.

**Output Format:**
Keywords: [keyword1, keyword2, keyword3, ...]

**Query to analyze:** {query}"""

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
                    model_names = [model['name'] for model in models['models']]
                    
                    if self.model_name not in model_names:
                        logger.warning(f"Model {self.model_name} not found. Available models: {model_names}")
                        logger.info(f"Attempting to pull model {self.model_name}...")
                        await self.client.pull(self.model_name)
                        logger.info(f"Successfully pulled model {self.model_name}")
                    else:
                        logger.info(f"Model {self.model_name} is available")
                        
                except Exception as e:
                    logger.error(f"Error checking/pulling model: {e}")
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
                    'temperature': 0.7,
                    'top_p': 0.9,
                    'max_tokens': 512,
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
            raise
    
    def _parse_classification_result(self, response: str, original_query: str = "") -> Dict[str, any]:
        """
        Parse the model response to extract domain and context
        
        Args:
            response: Raw model response
            original_query: Original user query for keyword extraction
            
        Returns:
            Parsed classification result
        """
        try:
            lines = response.strip().split('\n')
            domain = None
            context = None
            
            # Parse the structured output
            for line in lines:
                line = line.strip()
                if line.startswith('Domain:'):
                    domain = line.replace('Domain:', '').strip()
                elif line.startswith('Context:'):
                    context = line.replace('Context:', '').strip()
            
            # Validate domain - handle both single and multiple domains
            valid_domains = ['ai-robotics', 'geopolitics', 'out-of-domain']
            if domain:
                # Check if domain contains multiple domains (comma-separated)
                if ',' in domain:
                    domain_parts = [d.strip().lower() for d in domain.split(',')]
                    # Check if all parts are valid
                    if all(part in valid_domains for part in domain_parts):
                        # Extract keywords from context for backward compatibility
                        keywords = self._extract_keywords_from_context(context) if context else []
                        
                        return {
                            'domain': domain,
                            'context': context or '',
                            'keywords': keywords,
                            'confidence': self._calculate_confidence(response, domain)
                        }
                else:
                    # Single domain
                    if domain.lower() in valid_domains:
                        # Extract keywords based on domain type
                        if domain.lower() == 'out-of-domain':
                            # For out-of-domain, extract keywords from original query
                            keywords = self._extract_keywords_from_query(original_query) if original_query else []
                        else:
                            # For in-domain, extract keywords from context
                            keywords = self._extract_keywords_from_context(context) if context else []
                        
                        return {
                            'domain': domain,
                            'context': context or '',
                            'keywords': keywords,
                            'confidence': self._calculate_confidence(response, domain)
                        }
            else:
                # Fallback: try to extract domain from text
                domain = self._extract_domain_fallback(response)
                # Extract keywords from original query for fallback cases
                keywords = self._extract_keywords_from_query(original_query) if original_query else []
                return {
                    'domain': domain,
                    'context': response,
                    'keywords': keywords,
                    'confidence': 0.6
                }
                
        except Exception as e:
            logger.error(f"Error parsing classification result: {e}")
            # Extract keywords from original query for error cases
            keywords = self._extract_keywords_from_query(original_query) if original_query else []
            return {
                'domain': 'out-of-domain',
                'context': response,
                'keywords': keywords,
                'confidence': 0.0
            }
    
    def _extract_keywords_from_context(self, context: str) -> List[str]:
        """
        Extract keywords from context for backward compatibility
        
        Args:
            context: Context string
            
        Returns:
            List of keywords
        """
        if not context:
            return []
        
        # Simple keyword extraction - split by common separators
        keywords = []
        words = context.replace(',', ' ').replace('.', ' ').split()
        
        # Filter meaningful words (length > 3, not common words)
        common_words = {'what', 'are', 'the', 'how', 'why', 'when', 'where', 'which', 'who', 'this', 'that', 'with', 'from', 'into', 'onto', 'upon', 'about', 'above', 'below', 'between', 'among', 'through', 'during', 'before', 'after', 'since', 'until', 'while'}
        
        for word in words:
            word = word.lower().strip()
            if len(word) > 3 and word not in common_words:
                keywords.append(word)
        
        return keywords[:5]  # Limit to 5 keywords
    
    def _extract_keywords_from_query(self, query: str) -> List[str]:
        """
        Extract keywords directly from query for out-of-domain cases
        
        Args:
            query: Original user query
            
        Returns:
            List of keywords
        """
        if not query:
            return []
        
        # Simple keyword extraction from query
        keywords = []
        words = query.replace(',', ' ').replace('.', ' ').replace('?', ' ').split()
        
        # Filter meaningful words (length > 3, not common words)
        common_words = {'what', 'are', 'the', 'how', 'why', 'when', 'where', 'which', 'who', 'this', 'that', 'with', 'from', 'into', 'onto', 'upon', 'about', 'above', 'below', 'between', 'among', 'through', 'during', 'before', 'after', 'since', 'until', 'while', 'best', 'good', 'great', 'new', 'latest', 'recent'}
        
        for word in words:
            word = word.lower().strip()
            if len(word) > 3 and word not in common_words:
                keywords.append(word)
        
        return keywords[:5]  # Limit to 5 keywords
    
    def _extract_domain_fallback(self, response: str) -> str:
        """
        Fallback domain extraction from text response
        
        Args:
            response: Model response text
            
        Returns:
            Extracted domain
        """
        response_lower = response.lower()
        
        if any(term in response_lower for term in ['ai-robotics', 'artificial intelligence', 'robotics', 'machine learning']):
            return 'AI-Robotics'
        elif any(term in response_lower for term in ['geopolitics', 'international relations', 'political', 'geopolitical']):
            return 'Geopolitics'
        else:
            return 'out-of-domain'
    
    def _calculate_confidence(self, response: str, domain: str) -> float:
        """
        Calculate confidence score based on response quality
        
        Args:
            response: Model response
            domain: Classified domain
            
        Returns:
            Confidence score between 0 and 1
        """
        confidence = 0.5  # Base confidence
        
        # Increase confidence if structured format is present
        if 'Domain:' in response and 'Context:' in response:
            confidence += 0.3
        
        # Increase confidence for specific domains
        domain_lower = domain.lower()
        if domain_lower in ['ai-robotics', 'geopolitics'] or 'ai-robotics' in domain_lower or 'geopolitics' in domain_lower:
            confidence += 0.2
        
        # Increase confidence if context is meaningful
        if 'Context:' in response:
            context_line = [line for line in response.split('\n') if line.startswith('Context:')]
            if context_line and len(context_line[0].replace('Context:', '').strip()) > 10:
                confidence += 0.1
        
        return min(confidence, 1.0)
    
    async def classify_domain(self, query: str) -> Dict[str, any]:
        """
        Classify query domain and extract keywords
        
        Args:
            query: User query to classify
            
        Returns:
            Classification result with domain, keywords, and metadata
        """
        try:
            logger.info(f"Classifying query: {query[:100]}...")
            
            # Generate prompt
            prompt = ClassifierPrompts.get_classification_prompt(query)
            
            # Get model response
            response = await self._generate_response(prompt)
            
            # Parse result
            result = self._parse_classification_result(response, query)
            
            logger.info(f"Classification result: {result['domain']} (confidence: {result['confidence']:.2f})")
            logger.info(f"Context: {result.get('context', '')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in domain classification: {e}")
            # Extract keywords from original query for error cases
            keywords = self._extract_keywords_from_query(query) if query else []
            return {
                'domain': 'out-of-domain',
                'context': f'Error: {str(e)}',
                'keywords': keywords,
                'confidence': 0.0
            }
    
    async def classify_batch(self, queries: List[str]) -> List[Dict[str, any]]:
        """
        Classify multiple queries in batch
        
        Args:
            queries: List of queries to classify
            
        Returns:
            List of classification results
        """
        tasks = [self.classify_domain(query) for query in queries]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error classifying query {i}: {result}")
                # Extract keywords from original query for error cases
                original_query = queries[i] if i < len(queries) else ""
                keywords = self._extract_keywords_from_query(original_query) if original_query else []
                processed_results.append({
                    'domain': 'out-of-domain',
                    'context': f'Error: {str(result)}',
                    'keywords': keywords,
                    'confidence': 0.0
                })
            else:
                processed_results.append(result)
        
        return processed_results

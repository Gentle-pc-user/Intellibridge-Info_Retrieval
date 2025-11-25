"""
WebSearchAgent for searching and scraping recent content
Uses DuckDuckGo Search (DDGS) and BeautifulSoup for content retrieval
"""

import asyncio
import aiohttp
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse, urljoin
import random
import time
from config import DEFAULT_CONFIG

try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

from .utils import (
    setup_logging, clean_text, clean_filename, save_json, 
    extract_domain_from_url, is_recent_date, format_timestamp
)

logger = setup_logging()

class WebSearchPrompts:
    """Prompts for the WebSearchAgent"""
    
    SEARCH_STRATEGIES = {
        "ai-robotics": [
            "latest AI developments",
            "robotics innovation",
            "artificial intelligence news",
            "machine learning breakthroughs",
            "autonomous systems"
        ],
        "geopolitics": [
            "international relations",
            "geopolitical developments", 
            "political conflicts",
            "diplomatic news",
            "global affairs"
        ],
        "out-of-domain": [
            "general information",
            "how to",
            "best practices",
            "latest news",
            "recent developments"
        ]
    }
    
    @classmethod
    def get_search_queries(cls, domain: str, keywords: list) -> list:
        """Generate search queries based on domain and keywords"""
        # Normalize domain to lowercase for lookup
        domain_lower = domain.lower()
        
        # Handle multiple domains (comma-separated)
        if ',' in domain_lower:
            domains = [d.strip() for d in domain_lower.split(',')]
            base_queries = []
            for d in domains:
                base_queries.extend(cls.SEARCH_STRATEGIES.get(d, []))
        else:
            base_queries = cls.SEARCH_STRATEGIES.get(domain_lower, [])
        
        # Combine keywords with domain-specific terms
        queries = []
        for keyword in keywords[:3]:  # Limit to top 3 keywords
            queries.extend([
                f"{keyword} latest news",
                f"{keyword} recent developments",
                f"{keyword} 2024"
            ])
        
        # Add domain-specific queries
        queries.extend(base_queries[:2])
        
        return queries[:8]  # Limit total queries

class WebSearchAgent:
    """Agent responsible for web searching and content scraping"""
    
    def __init__(self, max_results_per_query: int = 10, max_scrape_per_query: int = 5):
        """
        Initialize the WebSearchAgent
        
        Args:
            max_results_per_query: Maximum search results per query
            max_scrape_per_query: Maximum articles to scrape per query
        """
        self.max_results_per_query = max_results_per_query
        self.max_scrape_per_query = max_scrape_per_query
        self.user_agent = UserAgent()
        
        # No domain filtering - search all domains
        
        logger.info("WebSearchAgent initialized")
    
    def _generate_search_queries(self, query: str, domain: str, keywords: List[str]) -> List[str]:
        """
        Generate search queries based on domain and keywords
        
        Args:
            query: Original user query
            domain: Classified domain
            keywords: Extracted keywords
            
        Returns:
            List of search queries
        """
        import re
        from datetime import datetime
        
        queries = []
        current_year = datetime.now().year
        
        # Extract year from query if mentioned
        query_year = None
        year_match = re.search(r'\b(20\d{2})\b', query)
        if year_match:
            query_year = int(year_match.group(1))
        
        # Check if query is about current information
        is_current_query = any(word in query.lower() for word in ['current', 'who is', 'latest', 'recent', 'new'])
        
        # Add original query variations
        queries.extend([
            f'"{query}"',
            f"{query} latest news",
            f"{query} recent developments"
        ])
        
        # For current/who is queries, prioritize recent information
        if is_current_query:
            queries.extend([
                f"{query} {current_year}",
                f"{query} 2025",
                f"latest {' '.join(keywords[:2])}",
                f"current {' '.join(keywords[:2])}",
                f"new {' '.join(keywords[:2])} {current_year}",
                f"{' '.join(keywords[:2])} news today"
            ])
        
        # Add year-specific queries if year is mentioned
        if query_year:
            queries.extend([
                f"{query} {query_year}",
                f"latest {' '.join(keywords[:2])} {query_year}",
                f"new {' '.join(keywords[:2])} {query_year}",
                f"{' '.join(keywords[:2])} developments {query_year}"
            ])
        else:
            # Add current year queries
            queries.extend([
                f"{query} {current_year}",
                f"latest {' '.join(keywords[:2])} {current_year}"
            ])
        
        # Add domain-specific queries
        domain_queries = WebSearchPrompts.get_search_queries(domain, keywords)
        queries.extend(domain_queries)
        
        # Add keyword-based queries with year focus
        for keyword in keywords[:3]:  # Limit to top 3 keywords
            target_year = query_year if query_year else current_year
            queries.extend([
                f'"{keyword}" latest',
                f"{keyword} news {target_year}",
                f"{keyword} {target_year}",
                f"{keyword} recent"
            ])
        
        return list(set(queries))[:10]  # Remove duplicates and allow more queries
    
    async def _search_duckduckgo(self, search_query: str) -> List[Dict[str, str]]:
        """
        Search using DuckDuckGo
        
        Args:
            search_query: Query to search
            
        Returns:
            List of search results
        """
        try:
            results = []
            
            with DDGS() as ddgs:
                # Try different time limits if no results found
                time_limits = ['d', 'w', 'm', None]
                
                for timelimit in time_limits:
                    try:
                        search_results = ddgs.text(
                            search_query,
                            max_results=self.max_results_per_query,
                            safesearch='moderate',
                            timelimit=timelimit
                        )
                        
                        for result in search_results:
                            href = result.get('href', '')
                            title = result.get('title', '')
                            body = result.get('body', '')
                            
                            if href and title and self._is_valid_url(href):
                                results.append({
                                    'title': clean_text(title),
                                    'url': href,
                                    'snippet': clean_text(body),
                                    'domain': extract_domain_from_url(href)
                                })
                        
                        # If we got results, break out of the loop
                        if results:
                            break
                            
                    except Exception as search_error:
                        logger.warning(f"Search with timelimit '{timelimit}' failed: {search_error}")
                        continue
            
            logger.info(f"Found {len(results)} results for query: {search_query}")
            return results
            
        except Exception as e:
            logger.error(f"Search failed for query '{search_query}': {e}")
            return []
    
    def _is_valid_url(self, url: str) -> bool:
        """
        Check if URL is valid and not blocked
        
        Args:
            url: URL to validate
            
        Returns:
            True if URL is valid
        """
        try:
            parsed = urlparse(url)
            
            # Must have scheme and netloc
            if not parsed.scheme or not parsed.netloc:
                return False
            
            # Must be HTTP or HTTPS
            if parsed.scheme not in ['http', 'https']:
                return False
            
            blocked_domains = [
                'facebook.com', 'twitter.com', 'instagram.com', 'youtube.com',
                'linkedin.com', 'pinterest.com', 'reddit.com', 'tiktok.com'
            ] + list(getattr(DEFAULT_CONFIG, 'BLOCKED_DOMAINS', []))
            
            domain = parsed.netloc.lower()
            if any(blocked in domain for blocked in blocked_domains):
                return False
            
            return True
            
        except:
            return False
    
    
    async def _scrape_article(self, session: aiohttp.ClientSession, url: str, 
                            title: str, snippet: str, query: str, 
                            keywords: List[str]) -> Optional[Dict[str, Any]]:
        """
        Scrape article content from URL
        
        Args:
            session: HTTP session
            url: Article URL
            title: Article title
            snippet: Article snippet
            query: Original query
            keywords: Extracted keywords
            
        Returns:
            Scraped article data or None
        """
        try:
            # Use minimal headers to avoid "Header value is too long" errors
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Cache-Control': 'no-cache',
            }
            
            # Random delay to avoid rate limiting
            await asyncio.sleep(random.uniform(0.5, 1.5))
            
            # No timeout - let it take as long as needed to scrape content
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    html = await response.text()
                    return self._extract_article_content(html, url, title, snippet, query, keywords)
                elif response.status == 429:
                    # Rate limited, wait longer
                    await asyncio.sleep(2)
                    return None
                else:
                    logger.warning(f"HTTP {response.status} for {url}")
                    return None
                    
        except asyncio.TimeoutError:
            logger.warning(f"Timeout scraping {url}")
            return None
        except Exception as e:
            logger.warning(f"Error scraping {url}: {e}")
            return None
    
    def _extract_article_content(self, html: str, url: str, title: str, 
                               snippet: str, query: str, keywords: List[str]) -> Dict[str, Any]:
        """
        Extract article content from HTML
        
        Args:
            html: HTML content
            url: Article URL
            title: Article title
            snippet: Article snippet
            query: Original query
            keywords: Extracted keywords
            
        Returns:
            Extracted article data
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove unwanted elements
            for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'ads']):
                element.decompose()
            
            # Extract main content
            content_selectors = [
                'article', '.article-body', '.story-content', '.main-content', 
                '.post-content', '.entry-content', '.content', 'main'
            ]
            
            content_text = ""
            for selector in content_selectors:
                container = soup.select_one(selector)
                if container:
                    paragraphs = container.find_all('p')
                    content_text = ' '.join([p.get_text().strip() for p in paragraphs])
                    if len(content_text) > 200:  # Found substantial content
                        break
            
            # Fallback to all paragraphs
            if not content_text:
                paragraphs = soup.find_all('p')
                content_text = ' '.join([p.get_text().strip() for p in paragraphs])
            
            # Extract publication date
            date_published = self._extract_publication_date(soup)
            
            # Extract author
            author = self._extract_author(soup)
            
            # Clean and limit content
            content_text = clean_text(content_text, max_length=5000)
            
            # Validate content quality - filter out low-quality content
            if self._is_low_quality_content(content_text):
                logger.warning(f"Low quality content detected for {url}, using fallback")
                # Instead of keeping snippets (which lead to headline-only answers),
                # drop content so downstream filters can exclude this article.
                content_text = ""
            
            return {
                'title': clean_text(title) or clean_filename(title),
                'content': content_text,
                'url': url,
                'domain': extract_domain_from_url(url),
                'author': author[:100] if author else "",
                'date_published': date_published,
                'query': query,
                'keywords': keywords,
                'scraped_at': format_timestamp(),
                'content_length': len(content_text),
                'relevance_score': self._calculate_relevance_score(title, content_text, keywords)
            }
            
        except Exception as e:
            logger.error(f"Error extracting content from {url}: {e}")
            return {
                'title': clean_text(title) or "Error extracting title",
                'content': f"Error extracting content: {str(e)}",
                'url': url,
                'domain': extract_domain_from_url(url),
                'author': "",
                'date_published': format_timestamp(),
                'query': query,
                'keywords': keywords,
                'scraped_at': format_timestamp(),
                'content_length': 0,
                'relevance_score': 0.0
            }
    
    def _extract_publication_date(self, soup: BeautifulSoup) -> str:
        """Extract publication date from article"""
        date_selectors = [
            'meta[property="article:published_time"]',
            'meta[name="date"]',
            'meta[name="publish-date"]',
            'time[datetime]',
            '.date',
            '.timestamp',
            '.publish-date'
        ]
        
        for selector in date_selectors:
            elements = soup.select(selector)
            for element in elements:
                date_str = (element.get("content") or 
                           element.get("datetime") or 
                           element.get_text().strip())
                if date_str:
                    try:
                        from dateutil.parser import parse as parse_date
                        parsed_date = parse_date(date_str)
                        return parsed_date.isoformat()
                    except:
                        continue
        
        return format_timestamp()
    
    def _extract_author(self, soup: BeautifulSoup) -> str:
        """Extract author from article"""
        author_selectors = [
            '.author', '.byline', 'meta[name="author"]', '.writer',
            '.reporter', '[rel="author"]'
        ]
        
        for selector in author_selectors:
            element = soup.select_one(selector)
            if element:
                if element.name == 'meta':
                    return element.get('content', '')
                else:
                    return element.get_text().strip()
        
        return ""
    
    def _calculate_relevance_score(self, title: str, content: str, keywords: List[str]) -> float:
        """
        Calculate relevance score for article
        
        Args:
            title: Article title
            content: Article content
            keywords: Relevant keywords
            
        Returns:
            Relevance score between 0 and 1
        """
        text = (title + ' ' + content).lower()
        score = 0.0
        
        # Check keyword presence
        for keyword in keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in text:
                score += 0.2
        
        # Check for recent indicators
        recent_indicators = ['today', 'latest', 'breaking', 'just in', 'now', 'update', 'new']
        for indicator in recent_indicators:
            if indicator in text:
                score += 0.1
        
        return min(score, 1.0)
    
    def _is_low_quality_content(self, content: str) -> bool:
        """
        Check if content is low quality and should be filtered out
        
        Args:
            content: Article content to check
            
        Returns:
            True if content is low quality
        """
        if not content or len(content.strip()) < 100:
            return True
            
        content_lower = content.lower().strip()
        
        # Common low-quality content indicators
        low_quality_indicators = [
            "please enable javascript",
            "javascript is required",
            "javascript must be enabled",
            "this site requires javascript",
            "enable cookies",
            "cookies are required",
            "access denied",
            "403 forbidden",
            "404 not found",
            "page not found",
            "error 404",
            "server error",
            "internal server error",
            "temporarily unavailable",
            "under maintenance",
            "coming soon",
            "subscribe to continue",
            "login required",
            "sign in to continue",
            "paywall",
            "premium content",
            "members only"
        ]
        
        # Check if content is mostly low-quality indicators
        for indicator in low_quality_indicators:
            if indicator in content_lower and len(content_lower) < 300:
                return True
        
        # Check if content is mostly repeated characters or words
        words = content_lower.split()
        if len(words) < 20:  # Too few words
            return True
            
        # Check for excessive repetition
        unique_words = set(words)
        if len(unique_words) < len(words) * 0.3:  # Less than 30% unique words
            return True
            
        return False
    
    def _prioritize_by_recency(self, results: List[Dict[str, str]], query: str) -> List[Dict[str, str]]:
        """
        Prioritize search results by recency indicators
        
        Args:
            results: List of search results
            query: Original query to extract year if mentioned
            
        Returns:
            Prioritized list of results
        """
        import re
        from datetime import datetime
        
        current_year = datetime.now().year
        
        # Extract year from query if mentioned
        query_year = None
        year_match = re.search(r'\b(20\d{2})\b', query)
        if year_match:
            query_year = int(year_match.group(1))
            logger.info(f"Detected year {query_year} in query")
        
        def calculate_recency_score(result):
            title = result.get('title', '').lower()
            snippet = result.get('snippet', '').lower()
            text = f"{title} {snippet}"
            domain = result.get('domain', '').lower()
            
            score = 0.0
            
            # Boost for specific year mentioned in query
            if query_year:
                if str(query_year) in text:
                    score += 10.0
                    logger.debug(f"Found query year {query_year} in: {title[:50]}...")
                # Penalize older years
                for year in range(2020, current_year):
                    if year != query_year and str(year) in text:
                        score -= 2.0
            
            # Boost for current year
            if str(current_year) in text:
                score += 8.0
                logger.debug(f"Found current year {current_year} in: {title[:50]}...")
            
            # Boost for recent indicators
            recent_indicators = [
                ('2025', 10.0), ('2024', 6.0), ('2023', 3.0),
                ('latest', 5.0), ('new', 4.0), ('recent', 4.0),
                ('breaking', 6.0), ('today', 7.0), ('now', 6.0),
                ('just released', 8.0), ('announced', 5.0),
                ('unveiled', 5.0), ('launched', 5.0),
                ('emerging', 4.0), ('cutting-edge', 4.0),
                ('breakthrough', 5.0), ('innovation', 3.0),
                ('update', 4.0), ('development', 3.0)
            ]
            
            for indicator, weight in recent_indicators:
                if indicator in text:
                    score += weight
            
            # Trusted domain boost
            try:
                trust_set = set(getattr(DEFAULT_CONFIG, 'TRUSTED_DOMAINS', []))
                if domain in trust_set:
                    score += 12.0
            except Exception:
                pass
            
            # Penalize very old years
            old_years = ['2022', '2021', '2020', '2019', '2018']
            for old_year in old_years:
                if old_year in text:
                    score -= 3.0
            
            return score
        
        # Calculate scores and sort
        scored_results = []
        for result in results:
            score = calculate_recency_score(result)
            scored_results.append((score, result))
        
        # Sort by score (highest first)
        scored_results.sort(key=lambda x: x[0], reverse=True)
        
        # Log top results for debugging
        logger.info("Top 5 prioritized results by recency:")
        for i, (score, result) in enumerate(scored_results[:5]):
            title = result.get('title', 'No title')[:60]
            logger.info(f"  {i+1}. Score: {score:.1f} - {title}...")
        
        return [result for score, result in scored_results]
    
    def _get_date_score(self, date_str: str) -> float:
        """
        Calculate a score based on how recent the date is
        
        Args:
            date_str: Date string to score
            
        Returns:
            Score (higher = more recent)
        """
        if not date_str:
            return 0.0
        
        try:
            from dateutil.parser import parse as parse_date
            from datetime import datetime
            
            parsed_date = parse_date(date_str)
            current_date = datetime.now()
            
            # Calculate days difference
            days_diff = (current_date - parsed_date).days
            
            # Score based on recency (higher score for more recent dates)
            if days_diff < 0:  # Future date (shouldn't happen but just in case)
                return 1000.0
            elif days_diff <= 30:  # Within last month
                return 1000.0 - days_diff
            elif days_diff <= 90:  # Within last 3 months
                return 900.0 - (days_diff - 30) * 2
            elif days_diff <= 365:  # Within last year
                return 700.0 - (days_diff - 90) * 0.5
            else:  # Older than a year
                return max(0.0, 500.0 - (days_diff - 365) * 0.1)
                
        except Exception as e:
            logger.debug(f"Error parsing date '{date_str}': {e}")
            return 0.0
    
    async def search_and_scrape(self, query: str, keywords: List[str], 
                              domain: str) -> List[Dict[str, Any]]:
        """
        Search and scrape relevant content
        
        Args:
            query: Original user query
            keywords: Extracted keywords
            domain: Classified domain
            
        Returns:
            List of scraped articles
        """
        try:
            logger.info(f"Starting search and scrape for query: {query}")
            
            # Generate search queries
            search_queries = self._generate_search_queries(query, domain, keywords)
            logger.info(f"Generated {len(search_queries)} search queries")
            
            # Search for each query
            all_results = []
            for search_query in search_queries:
                results = await self._search_duckduckgo(search_query)
                all_results.extend(results)
                
                # Short delay between searches
                await asyncio.sleep(1)
            
            # Remove duplicates
            seen_urls = set()
            unique_results = []
            for result in all_results:
                if result['url'] not in seen_urls:
                    seen_urls.add(result['url'])
                    unique_results.append(result)
            
            # Prioritize results by recency indicators in title/snippet
            prioritized_results = self._prioritize_by_recency(unique_results, query)
            
            # Limit to reasonable number for scraping
            prioritized_results = prioritized_results[:self.max_scrape_per_query * 3]
            
            logger.info(f"Found {len(prioritized_results)} prioritized results")
            
            # Scrape articles
            scraped_articles = []
            
            # Use more conservative connection settings to prevent errors
            connector = aiohttp.TCPConnector(
                limit=5, 
                limit_per_host=2,
                ttl_dns_cache=300,
                use_dns_cache=True,
                keepalive_timeout=30,
                enable_cleanup_closed=True
            )
            timeout = aiohttp.ClientTimeout(total=None, connect=10)  # No total timeout, only connect timeout
            
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                # Process articles concurrently with semaphore
                semaphore = asyncio.Semaphore(3)
                
                async def scrape_with_semaphore(result):
                    async with semaphore:
                        return await self._scrape_article(
                            session, result['url'], result['title'], 
                            result['snippet'], query, keywords
                        )
                
                tasks = [scrape_with_semaphore(result) for result in prioritized_results]
                scraped_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results and filter out low-quality articles
                for result in scraped_results:
                    if isinstance(result, dict) and result:
                        content = result.get('content', '')
                        content_length = len(content.strip())
                        
                        # Only include articles with substantial content
                        if content_length >= 100 and not self._is_low_quality_content(content):
                            scraped_articles.append(result)
                            logger.debug(f"Added article: {result.get('title', 'Unknown')[:50]}... ({content_length} chars)")
                        else:
                            logger.warning(f"Filtered out low-quality article: {result.get('title', 'Unknown')[:50]}... ({content_length} chars)")
                    elif isinstance(result, Exception):
                        logger.error(f"Scraping error: {result}")
            
            # Sort by publication date (most recent first), then relevance and quality
            scraped_articles.sort(
                key=lambda x: (
                    self._get_date_score(x.get('date_published', '')),
                    1 if x.get('domain', '') in getattr(DEFAULT_CONFIG, 'TRUSTED_DOMAINS', []) else 0,
                    x['relevance_score'], 
                    x['content_length']
                ),
                reverse=True
            )
            
            # Log final articles for debugging
            logger.info("Final articles selected (by recency):")
            for i, article in enumerate(scraped_articles[:self.max_scrape_per_query]):
                title = article.get('title', 'No title')[:50]
                date = article.get('date_published', 'No date')
                logger.info(f"  {i+1}. {title}... (Date: {date})")
            
            # Limit final results
            final_articles = scraped_articles[:self.max_scrape_per_query]
            
            # Save scraped data
            if final_articles:
                self._save_scraped_data(query, domain, final_articles)
            
            logger.info(f"Successfully scraped {len(final_articles)} articles")
            return final_articles
            
        except Exception as e:
            logger.error(f"Error in search and scrape: {e}")
            return []
    
    def _save_scraped_data(self, query: str, domain: str, articles: List[Dict[str, Any]]):
        """
        Save scraped data to JSON file
        
        Args:
            query: Original query
            domain: Classified domain
            articles: Scraped articles
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"data/scraped/scraped_{timestamp}_{clean_filename(query)[:50]}.json"
            
            data = {
                'metadata': {
                    'query': query,
                    'domain': domain,
                    'scraped_at': format_timestamp(),
                    'article_count': len(articles),
                    'total_content_length': sum(art['content_length'] for art in articles)
                },
                'articles': articles
            }
            
            if save_json(data, filename):
                logger.info(f"Saved scraped data to {filename}")
            
        except Exception as e:
            logger.error(f"Error saving scraped data: {e}")

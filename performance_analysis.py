#!/usr/bin/env python3
"""
Comprehensive Performance Analysis for Multi-Agent System
Tests all components and measures execution times, accuracy, and quality metrics.
"""

import asyncio
import time
import json
import statistics
from typing import Dict, List, Any, Tuple
from datetime import datetime
import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.keywords_agent import KeywordsAgent
from agents.websearch_agent import WebSearchAgent
from agents.response_agent import ResponseAgent
from agents.classifier_agent import ClassifierAgent
from config import Config

class PerformanceAnalyzer:
    """Comprehensive performance analyzer for the multi-agent system"""
    
    def __init__(self):
        self.config = Config()
        self.results = {
            'keyword_extraction': [],
            'websearch': [],
            'scraping': [],
            'response_generation': [],
            'end_to_end': [],
            'embedding_performance': [],
            'retrieval_performance': []
        }
        self.test_queries = [
            "current prime minister of Japan",
            "latest AI developments 2024",
            "Trump tariffs recent news",
            "quantum computing breakthroughs",
            "Russia Ukraine conflict latest",
            "healthcare technology trends",
            "climate change policies 2024",
            "stock market performance today",
            "electric vehicle market share",
            "artificial intelligence regulation"
        ]
        
    async def setup_agents(self):
        """Initialize all agents"""
        self.keywords_agent = KeywordsAgent()
        self.websearch_agent = WebSearchAgent()
        self.response_agent = ResponseAgent()
        self.classifier_agent = ClassifierAgent()
        
    async def test_keyword_extraction(self) -> Dict[str, Any]:
        """Test keyword extraction performance"""
        print("\n=== Testing Keyword Extraction ===")
        results = []
        
        for query in self.test_queries:
            start_time = time.time()
            
            try:
                result = await self.keywords_agent.extract_keywords(query)
                end_time = time.time()
                
                execution_time = end_time - start_time
                
                # Analyze keyword quality
                keywords = result.get('keywords', [])
                confidence = result.get('confidence', 0)
                
                # Metrics
                keyword_count = len(keywords)
                avg_keyword_length = statistics.mean([len(kw) for kw in keywords]) if keywords else 0
                relevance_score = self._calculate_keyword_relevance(query, keywords)
                
                result_data = {
                    'query': query,
                    'execution_time': execution_time,
                    'keyword_count': keyword_count,
                    'keywords': keywords,
                    'confidence': confidence,
                    'avg_keyword_length': avg_keyword_length,
                    'relevance_score': relevance_score,
                    'quality_issues': self._identify_keyword_issues(query, keywords)
                }
                
                results.append(result_data)
                print(f"✓ '{query[:30]}...' - {execution_time:.2f}s - {keyword_count} keywords (relevance: {relevance_score:.2f})")
                
            except Exception as e:
                print(f"✗ '{query[:30]}...' - ERROR: {e}")
                results.append({
                    'query': query,
                    'execution_time': 0,
                    'error': str(e),
                    'keyword_count': 0,
                    'relevance_score': 0
                })
        
        # Calculate aggregate metrics
        execution_times = [r['execution_time'] for r in results if 'execution_time' in r]
        relevance_scores = [r['relevance_score'] for r in results if 'relevance_score' in r]
        
        summary = {
            'total_queries': len(self.test_queries),
            'successful_queries': len([r for r in results if 'error' not in r]),
            'avg_execution_time': statistics.mean(execution_times) if execution_times else 0,
            'min_execution_time': min(execution_times) if execution_times else 0,
            'max_execution_time': max(execution_times) if execution_times else 0,
            'avg_relevance_score': statistics.mean(relevance_scores) if relevance_scores else 0,
            'avg_keyword_count': statistics.mean([r['keyword_count'] for r in results if 'keyword_count' in r]) if results else 0,
            'detailed_results': results
        }
        
        self.results['keyword_extraction'] = summary
        return summary
    
    async def test_websearch_performance(self) -> Dict[str, Any]:
        """Test DuckDuckGo search performance"""
        print("\n=== Testing WebSearch Performance ===")
        results = []
        
        # Test with a subset of queries to avoid rate limiting
        test_queries = self.test_queries[:5]
        
        for query in test_queries:
            start_time = time.time()
            
            try:
                # First extract keywords
                keyword_result = await self.keywords_agent.extract_keywords(query)
                keywords = keyword_result.get('keywords', [])
                
                # Classify domain
                domain_result = await self.classifier_agent.classify_query(query)
                domain = domain_result.get('domain', 'general')
                
                # Test search
                search_results = await self.websearch_agent._search_duckduckgo(query)
                end_time = time.time()
                
                execution_time = end_time - start_time
                
                # Analyze search results
                result_count = len(search_results)
                unique_domains = len(set([r.get('domain', '') for r in search_results]))
                duplicate_urls = len(search_results) - len(set([r.get('url', '') for r in search_results]))
                
                # Quality assessment
                avg_snippet_length = statistics.mean([len(r.get('snippet', '')) for r in search_results]) if search_results else 0
                relevance_score = self._calculate_search_relevance(query, search_results)
                
                result_data = {
                    'query': query,
                    'execution_time': execution_time,
                    'result_count': result_count,
                    'unique_domains': unique_domains,
                    'duplicate_urls': duplicate_urls,
                    'avg_snippet_length': avg_snippet_length,
                    'relevance_score': relevance_score,
                    'keywords_used': keywords,
                    'domain_classification': domain
                }
                
                results.append(result_data)
                print(f"✓ '{query[:30]}...' - {execution_time:.2f}s - {result_count} results (relevance: {relevance_score:.2f})")
                
            except Exception as e:
                print(f"✗ '{query[:30]}...' - ERROR: {e}")
                results.append({
                    'query': query,
                    'execution_time': 0,
                    'error': str(e),
                    'result_count': 0,
                    'relevance_score': 0
                })
        
        # Calculate aggregate metrics
        execution_times = [r['execution_time'] for r in results if 'execution_time' in r]
        relevance_scores = [r['relevance_score'] for r in results if 'relevance_score' in r]
        
        summary = {
            'total_queries': len(test_queries),
            'successful_queries': len([r for r in results if 'error' not in r]),
            'avg_execution_time': statistics.mean(execution_times) if execution_times else 0,
            'min_execution_time': min(execution_times) if execution_times else 0,
            'max_execution_time': max(execution_times) if execution_times else 0,
            'avg_relevance_score': statistics.mean(relevance_scores) if relevance_scores else 0,
            'avg_result_count': statistics.mean([r['result_count'] for r in results if 'result_count' in r]) if results else 0,
            'duplicate_rate': statistics.mean([r['duplicate_urls']/max(r['result_count'], 1) for r in results if 'result_count' in r]) if results else 0,
            'detailed_results': results
        }
        
        self.results['websearch'] = summary
        return summary
    
    async def test_scraping_performance(self) -> Dict[str, Any]:
        """Test web scraping performance and quality"""
        print("\n=== Testing Scraping Performance ===")
        results = []
        
        # Test with a small subset
        test_query = "artificial intelligence latest news"
        
        try:
            start_time = time.time()
            
            # Extract keywords and classify
            keyword_result = await self.keywords_agent.extract_keywords(test_query)
            keywords = keyword_result.get('keywords', [])
            
            domain_result = await self.classifier_agent.classify_query(test_query)
            domain = domain_result.get('domain', 'technology')
            
            # Search and scrape
            scraped_articles = await self.websearch_agent.search_and_scrape(test_query, keywords, domain)
            end_time = time.time()
            
            execution_time = end_time - start_time
            
            # Analyze scraped content
            article_count = len(scraped_articles)
            total_content_length = sum([len(article.get('content', '')) for article in scraped_articles])
            avg_content_length = total_content_length / article_count if article_count > 0 else 0
            
            # Quality metrics
            quality_articles = [art for art in scraped_articles if not self.websearch_agent._is_low_quality_content(art.get('content', ''))]
            quality_rate = len(quality_articles) / article_count if article_count > 0 else 0
            
            # Content cleanliness
            clean_articles = 0
            for article in scraped_articles:
                content = article.get('content', '')
                if self._assess_content_cleanliness(content):
                    clean_articles += 1
            
            cleanliness_rate = clean_articles / article_count if article_count > 0 else 0
            
            result_data = {
                'query': test_query,
                'execution_time': execution_time,
                'articles_scraped': article_count,
                'total_content_length': total_content_length,
                'avg_content_length': avg_content_length,
                'quality_rate': quality_rate,
                'cleanliness_rate': cleanliness_rate,
                'keywords_used': keywords,
                'issues_found': self._identify_scraping_issues(scraped_articles)
            }
            
            results.append(result_data)
            print(f"✓ Scraped {article_count} articles in {execution_time:.2f}s (quality: {quality_rate:.2f}, clean: {cleanliness_rate:.2f})")
            
        except Exception as e:
            print(f"✗ Scraping test failed: {e}")
            results.append({
                'query': test_query,
                'execution_time': 0,
                'error': str(e),
                'articles_scraped': 0
            })
        
        summary = {
            'total_tests': 1,
            'successful_tests': len([r for r in results if 'error' not in r]),
            'avg_execution_time': results[0]['execution_time'] if results and 'execution_time' in results[0] else 0,
            'total_articles_scraped': results[0]['articles_scraped'] if results else 0,
            'avg_content_length': results[0]['avg_content_length'] if results and 'avg_content_length' in results[0] else 0,
            'quality_rate': results[0]['quality_rate'] if results and 'quality_rate' in results[0] else 0,
            'cleanliness_rate': results[0]['cleanliness_rate'] if results and 'cleanliness_rate' in results[0] else 0,
            'detailed_results': results
        }
        
        self.results['scraping'] = summary
        return summary
    
    async def test_response_generation(self) -> Dict[str, Any]:
        """Test LLM response generation performance"""
        print("\n=== Testing Response Generation ===")
        results = []
        
        # Test with a subset of queries
        test_queries = self.test_queries[:3]
        
        for query in test_queries:
            start_time = time.time()
            
            try:
                # Simulate having some scraped data
                mock_scraped_data = [
                    {
                        'title': f'Relevant article for {query}',
                        'content': f'This is a sample content about {query}. It contains relevant information that would help answer the user\'s question.',
                        'url': 'https://example.com/article1',
                        'domain': 'example.com'
                    }
                ]
                
                # Generate response
                response = await self.response_agent.generate_response(query, mock_scraped_data)
                end_time = time.time()
                
                execution_time = end_time - start_time
                
                # Analyze response quality
                response_length = len(response.get('response', ''))
                has_sources = bool(response.get('sources'))
                success = response.get('success', False)
                
                result_data = {
                    'query': query,
                    'execution_time': execution_time,
                    'response_length': response_length,
                    'has_sources': has_sources,
                    'success': success,
                    'response_preview': response.get('response', '')[:200] + '...' if response.get('response') else ''
                }
                
                results.append(result_data)
                print(f"✓ '{query[:30]}...' - {execution_time:.2f}s - {response_length} chars (success: {success})")
                
            except Exception as e:
                print(f"✗ '{query[:30]}...' - ERROR: {e}")
                results.append({
                    'query': query,
                    'execution_time': 0,
                    'error': str(e),
                    'success': False
                })
        
        # Calculate aggregate metrics
        execution_times = [r['execution_time'] for r in results if 'execution_time' in r]
        success_rate = len([r for r in results if r.get('success', False)]) / len(results) if results else 0
        
        summary = {
            'total_queries': len(test_queries),
            'successful_queries': len([r for r in results if 'error' not in r]),
            'success_rate': success_rate,
            'avg_execution_time': statistics.mean(execution_times) if execution_times else 0,
            'min_execution_time': min(execution_times) if execution_times else 0,
            'max_execution_time': max(execution_times) if execution_times else 0,
            'avg_response_length': statistics.mean([r['response_length'] for r in results if 'response_length' in r]) if results else 0,
            'detailed_results': results
        }
        
        self.results['response_generation'] = summary
        return summary
    
    async def test_end_to_end_performance(self) -> Dict[str, Any]:
        """Test complete pipeline performance"""
        print("\n=== Testing End-to-End Performance ===")
        results = []
        
        # Test with a small subset
        test_queries = self.test_queries[:2]
        
        for query in test_queries:
            start_time = time.time()
            
            try:
                # Step 1: Classification
                classification_start = time.time()
                domain_result = await self.classifier_agent.classify_query(query)
                classification_time = time.time() - classification_start
                
                # Step 2: Keyword extraction
                keywords_start = time.time()
                keyword_result = await self.keywords_agent.extract_keywords(query)
                keywords_time = time.time() - keywords_start
                
                # Step 3: Web search and scraping
                search_start = time.time()
                scraped_data = await self.websearch_agent.search_and_scrape(
                    query, 
                    keyword_result.get('keywords', []), 
                    domain_result.get('domain', 'general')
                )
                search_time = time.time() - search_start
                
                # Step 4: Response generation
                response_start = time.time()
                response = await self.response_agent.generate_response(query, scraped_data)
                response_time = time.time() - response_start
                
                total_time = time.time() - start_time
                
                result_data = {
                    'query': query,
                    'total_execution_time': total_time,
                    'classification_time': classification_time,
                    'keywords_time': keywords_time,
                    'search_time': search_time,
                    'response_time': response_time,
                    'articles_found': len(scraped_data),
                    'response_success': response.get('success', False),
                    'domain_classified': domain_result.get('domain', ''),
                    'keywords_extracted': len(keyword_result.get('keywords', [])),
                    'bottleneck': max([
                        ('classification', classification_time),
                        ('keywords', keywords_time),
                        ('search', search_time),
                        ('response', response_time)
                    ], key=lambda x: x[1])[0]
                }
                
                results.append(result_data)
                print(f"✓ '{query[:30]}...' - Total: {total_time:.2f}s (Articles: {len(scraped_data)}, Success: {response.get('success', False)})")
                
            except Exception as e:
                print(f"✗ '{query[:30]}...' - ERROR: {e}")
                results.append({
                    'query': query,
                    'total_execution_time': 0,
                    'error': str(e),
                    'response_success': False
                })
        
        # Calculate aggregate metrics
        execution_times = [r['total_execution_time'] for r in results if 'total_execution_time' in r]
        
        summary = {
            'total_queries': len(test_queries),
            'successful_queries': len([r for r in results if 'error' not in r]),
            'avg_total_time': statistics.mean(execution_times) if execution_times else 0,
            'min_total_time': min(execution_times) if execution_times else 0,
            'max_total_time': max(execution_times) if execution_times else 0,
            'avg_articles_found': statistics.mean([r['articles_found'] for r in results if 'articles_found' in r]) if results else 0,
            'success_rate': len([r for r in results if r.get('response_success', False)]) / len(results) if results else 0,
            'common_bottlenecks': [r['bottleneck'] for r in results if 'bottleneck' in r],
            'detailed_results': results
        }
        
        self.results['end_to_end'] = summary
        return summary
    
    def _calculate_keyword_relevance(self, query: str, keywords: List[str]) -> float:
        """Calculate relevance score for keywords"""
        if not keywords:
            return 0.0
        
        query_words = set(query.lower().split())
        keyword_words = set(' '.join(keywords).lower().split())
        
        # Calculate overlap
        intersection = query_words.intersection(keyword_words)
        relevance = len(intersection) / len(query_words) if query_words else 0
        
        # Bonus for specific, meaningful keywords
        specific_bonus = sum(1 for kw in keywords if len(kw) > 3) / len(keywords) if keywords else 0
        
        return min(1.0, relevance + specific_bonus * 0.3)
    
    def _calculate_search_relevance(self, query: str, results: List[Dict]) -> float:
        """Calculate relevance score for search results"""
        if not results:
            return 0.0
        
        query_words = set(query.lower().split())
        relevance_scores = []
        
        for result in results:
            title_words = set(result.get('title', '').lower().split())
            snippet_words = set(result.get('snippet', '').lower().split())
            
            # Check for query words in title and snippet
            title_relevance = len(query_words.intersection(title_words)) / len(query_words) if query_words else 0
            snippet_relevance = len(query_words.intersection(snippet_words)) / len(query_words) if query_words else 0
            
            # Weight title more heavily
            combined_relevance = (title_relevance * 0.7 + snippet_relevance * 0.3)
            relevance_scores.append(combined_relevance)
        
        return statistics.mean(relevance_scores) if relevance_scores else 0.0
    
    def _identify_keyword_issues(self, query: str, keywords: List[str]) -> List[str]:
        """Identify issues with extracted keywords"""
        issues = []
        
        if len(keywords) == 0:
            issues.append("No keywords extracted")
        elif len(keywords) > 8:
            issues.append("Too many keywords")
        elif len(keywords) < 2:
            issues.append("Too few keywords")
        
        # Check for overly generic keywords
        generic_keywords = {'latest', 'news', 'information', 'about', 'what', 'how'}
        generic_count = sum(1 for kw in keywords if kw.lower() in generic_keywords)
        if generic_count > len(keywords) * 0.5:
            issues.append("Too many generic keywords")
        
        return issues
    
    def _identify_scraping_issues(self, articles: List[Dict]) -> List[str]:
        """Identify issues with scraped articles"""
        issues = []
        
        if not articles:
            issues.append("No articles scraped")
            return issues
        
        # Check for short content
        short_articles = [art for art in articles if len(art.get('content', '')) < 200]
        if len(short_articles) > len(articles) * 0.5:
            issues.append("Many articles with short content")
        
        # Check for JavaScript/paywall indicators
        js_indicators = ['javascript', 'enable javascript', 'please enable', 'subscription required']
        js_articles = 0
        for article in articles:
            content = article.get('content', '').lower()
            if any(indicator in content for indicator in js_indicators):
                js_articles += 1
        
        if js_articles > len(articles) * 0.3:
            issues.append("Many articles require JavaScript or have paywalls")
        
        return issues
    
    def _assess_content_cleanliness(self, content: str) -> bool:
        """Assess if content is clean (free of HTML, scripts, ads)"""
        if not content:
            return False
        
        # Check for HTML tags
        if '<' in content and '>' in content:
            return False
        
        # Check for script/ad indicators
        ad_indicators = ['advertisement', 'ads by', 'google-ad', 'script', 'function()', 'var ', 'let ']
        content_lower = content.lower()
        
        ad_count = sum(1 for indicator in ad_indicators if indicator in content_lower)
        if ad_count > 2:
            return False
        
        # Check for minimum meaningful content
        if len(content.strip()) < 100:
            return False
        
        return True
    
    def generate_report(self) -> str:
        """Generate comprehensive performance report"""
        report = []
        report.append("# Multi-Agent System Performance Analysis Report")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Keyword Extraction Summary
        if self.results['keyword_extraction']:
            ke = self.results['keyword_extraction']
            report.append("## Keyword Extraction Performance")
            report.append(f"- **Average Execution Time**: {ke['avg_execution_time']:.2f}s")
            report.append(f"- **Success Rate**: {ke['successful_queries']}/{ke['total_queries']} ({ke['successful_queries']/ke['total_queries']*100:.1f}%)")
            report.append(f"- **Average Relevance Score**: {ke['avg_relevance_score']:.2f}")
            report.append(f"- **Average Keywords per Query**: {ke['avg_keyword_count']:.1f}")
            report.append(f"- **Execution Time Range**: {ke['min_execution_time']:.2f}s - {ke['max_execution_time']:.2f}s")
            report.append("")
        
        # WebSearch Summary
        if self.results['websearch']:
            ws = self.results['websearch']
            report.append("## WebSearch Performance")
            report.append(f"- **Average Execution Time**: {ws['avg_execution_time']:.2f}s")
            report.append(f"- **Success Rate**: {ws['successful_queries']}/{ws['total_queries']} ({ws['successful_queries']/ws['total_queries']*100:.1f}%)")
            report.append(f"- **Average Results per Query**: {ws['avg_result_count']:.1f}")
            report.append(f"- **Average Relevance Score**: {ws['avg_relevance_score']:.2f}")
            report.append(f"- **Duplicate Rate**: {ws['duplicate_rate']:.2%}")
            report.append("")
        
        # Scraping Summary
        if self.results['scraping']:
            sc = self.results['scraping']
            report.append("## Web Scraping Performance")
            report.append(f"- **Execution Time**: {sc['avg_execution_time']:.2f}s")
            report.append(f"- **Articles Scraped**: {sc['total_articles_scraped']}")
            report.append(f"- **Average Content Length**: {sc['avg_content_length']:.0f} chars")
            report.append(f"- **Content Quality Rate**: {sc['quality_rate']:.2%}")
            report.append(f"- **Content Cleanliness Rate**: {sc['cleanliness_rate']:.2%}")
            report.append("")
        
        # Response Generation Summary
        if self.results['response_generation']:
            rg = self.results['response_generation']
            report.append("## Response Generation Performance")
            report.append(f"- **Average Execution Time**: {rg['avg_execution_time']:.2f}s")
            report.append(f"- **Success Rate**: {rg['success_rate']:.2%}")
            report.append(f"- **Average Response Length**: {rg['avg_response_length']:.0f} chars")
            report.append(f"- **Execution Time Range**: {rg['min_execution_time']:.2f}s - {rg['max_execution_time']:.2f}s")
            report.append("")
        
        # End-to-End Summary
        if self.results['end_to_end']:
            e2e = self.results['end_to_end']
            report.append("## End-to-End Pipeline Performance")
            report.append(f"- **Average Total Time**: {e2e['avg_total_time']:.2f}s")
            report.append(f"- **Success Rate**: {e2e['success_rate']:.2%}")
            report.append(f"- **Average Articles Found**: {e2e['avg_articles_found']:.1f}")
            report.append(f"- **Common Bottleneck**: {max(set(e2e['common_bottlenecks']), key=e2e['common_bottlenecks'].count) if e2e['common_bottlenecks'] else 'N/A'}")
            report.append("")
        
        # Performance Issues and Recommendations
        report.append("## Performance Issues and Recommendations")
        
        # Identify bottlenecks
        bottlenecks = []
        if self.results['keyword_extraction'] and self.results['keyword_extraction']['avg_execution_time'] > 3:
            bottlenecks.append("Keyword extraction is slow (>3s)")
        if self.results['websearch'] and self.results['websearch']['avg_execution_time'] > 5:
            bottlenecks.append("Web search is slow (>5s)")
        if self.results['response_generation'] and self.results['response_generation']['avg_execution_time'] > 10:
            bottlenecks.append("Response generation is slow (>10s)")
        
        if bottlenecks:
            report.append("### Identified Bottlenecks:")
            for bottleneck in bottlenecks:
                report.append(f"- {bottleneck}")
            report.append("")
        
        # Quality issues
        quality_issues = []
        if self.results['keyword_extraction'] and self.results['keyword_extraction']['avg_relevance_score'] < 0.6:
            quality_issues.append("Low keyword relevance (<0.6)")
        if self.results['websearch'] and self.results['websearch']['avg_relevance_score'] < 0.5:
            quality_issues.append("Low search result relevance (<0.5)")
        if self.results['scraping'] and self.results['scraping']['quality_rate'] < 0.7:
            quality_issues.append("Low content quality rate (<70%)")
        
        if quality_issues:
            report.append("### Quality Issues:")
            for issue in quality_issues:
                report.append(f"- {issue}")
            report.append("")
        
        # Recommendations
        report.append("### Recommendations:")
        report.append("1. **Optimize Keyword Extraction**: Consider caching or using faster models")
        report.append("2. **Improve Search Quality**: Add better query optimization and filtering")
        report.append("3. **Enhance Content Cleaning**: Implement better HTML parsing and noise removal")
        report.append("4. **Add Caching**: Cache search results and scraped content")
        report.append("5. **Implement Rate Limiting**: Add proper delays between requests")
        report.append("6. **Monitor Performance**: Set up continuous performance monitoring")
        
        return "\n".join(report)
    
    async def run_full_analysis(self) -> Dict[str, Any]:
        """Run complete performance analysis"""
        print("🚀 Starting Comprehensive Performance Analysis...")
        print("=" * 60)
        
        await self.setup_agents()
        
        # Run all tests
        await self.test_keyword_extraction()
        await self.test_websearch_performance()
        await self.test_scraping_performance()
        await self.test_response_generation()
        await self.test_end_to_end_performance()
        
        # Generate report
        report = self.generate_report()
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save detailed results
        with open(f'performance_results_{timestamp}.json', 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        # Save report
        with open(f'performance_report_{timestamp}.md', 'w') as f:
            f.write(report)
        
        print("\n" + "=" * 60)
        print("✅ Performance Analysis Complete!")
        print(f"📊 Detailed results saved to: performance_results_{timestamp}.json")
        print(f"📄 Report saved to: performance_report_{timestamp}.md")
        print("\n" + report)
        
        return self.results

# Main execution
async def main():
    analyzer = PerformanceAnalyzer()
    await analyzer.run_full_analysis()

if __name__ == "__main__":
    asyncio.run(main())

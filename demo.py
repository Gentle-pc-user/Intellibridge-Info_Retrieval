"""
Demo script for the Multi-Agent System
Demonstrates the system capabilities with sample queries
"""

import asyncio
import json
from datetime import datetime

from agents.classifier_agent import ClassifierAgent
from agents.websearch_agent import WebSearchAgent
from agents.response_agent import ResponseAgent
from agents.utils import setup_logging

# Setup logging
logger = setup_logging()

class MultiAgentDemo:
    """Demo class for testing the multi-agent system"""
    
    def __init__(self):
        self.classifier = ClassifierAgent(model_name="llama3.2-vision")
        self.websearch = WebSearchAgent()
        self.response = ResponseAgent(llm_model_name="llama3.2-vision")
        
    async def run_demo_query(self, query: str) -> dict:
        """
        Run a complete demo query through the pipeline
        
        Args:
            query: Demo query to process
            
        Returns:
            Complete processing result
        """
        print(f"\n{'='*60}")
        print(f"🔍 DEMO QUERY: {query}")
        print(f"{'='*60}")
        
        start_time = datetime.now()
        
        try:
            # Step 1: Classification
            print("\n📊 Step 1: Domain Classification")
            classification = await self.classifier.classify_domain(query)
            print(f"   Domain: {classification['domain']}")
            print(f"   Context: {classification.get('context', 'N/A')}")
            print(f"   Keywords: {classification['keywords']}")
            print(f"   Confidence: {classification['confidence']:.2f}")
            
            # Step 2: Web Search & Scraping
            print("\n🌐 Step 2: Web Search & Scraping")
            scraped_data = await self.websearch.search_and_scrape(
                query=query,
                keywords=classification['keywords'],
                domain=classification['domain']
            )
            print(f"   Articles found: {len(scraped_data)}")
            
            if scraped_data:
                print("   Sample articles:")
                for i, article in enumerate(scraped_data[:3], 1):
                    print(f"     {i}. {article['title'][:80]}...")
                    print(f"        Source: {article['domain']}")
                    print(f"        Length: {article['content_length']} chars")
            
            # Step 3: Response Generation
            print("\n🤖 Step 3: Response Generation")
            response = await self.response.generate_response(
                query=query,
                domain=classification['domain'],
                keywords=classification['keywords'],
                scraped_data=scraped_data
            )
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            result = {
                'query': query,
                'classification': classification,
                'scraped_articles': len(scraped_data),
                'response': response,
                'processing_time': duration,
                'timestamp': datetime.now().isoformat()
            }
            
            print(f"\n⏱️  Total Processing Time: {duration:.2f} seconds")
            print(f"\n📝 FINAL RESPONSE:")
            print(f"{'-'*60}")
            print(response)
            print(f"{'-'*60}")
            
            return result
            
        except Exception as e:
            logger.error(f"Demo query failed: {e}")
            print(f"\n❌ ERROR: {e}")
            return {
                'query': query,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

async def run_demo():
    """Run the complete demo with sample queries"""
    
    print("🚀 MULTI-AGENT SYSTEM DEMO")
    print("=" * 60)
    print("Testing the AI-Robotics and Geopolitics classification system")
    print("=" * 60)
    
    demo = MultiAgentDemo()
    
    # Sample queries for different domains
    sample_queries = [
        # AI-Robotics queries
        "What are the latest developments in autonomous drone navigation systems?",
        "How is artificial intelligence being used in robotic surgery?",
        "What are the newest breakthroughs in computer vision for autonomous vehicles?",
        
        # Geopolitics queries
        "How is the Russia-Ukraine conflict affecting global energy markets?",
        "What are the implications of China's Belt and Road Initiative?",
        "How are trade tensions between US and China evolving?",
        
        # Out-of-domain query
        "What's the best recipe for chocolate cake?"
    ]
    
    results = []
    
    for i, query in enumerate(sample_queries, 1):
        print(f"\n🎯 DEMO {i}/{len(sample_queries)}")
        result = await demo.run_demo_query(query)
        results.append(result)
        
        # Add delay between queries
        if i < len(sample_queries):
            print("\n⏳ Waiting 3 seconds before next query...")
            await asyncio.sleep(3)
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 DEMO SUMMARY")
    print(f"{'='*60}")
    
    successful_queries = [r for r in results if 'error' not in r]
    failed_queries = [r for r in results if 'error' in r]
    
    print(f"Total queries: {len(results)}")
    print(f"Successful: {len(successful_queries)}")
    print(f"Failed: {len(failed_queries)}")
    
    if successful_queries:
        avg_time = sum(r['processing_time'] for r in successful_queries) / len(successful_queries)
        print(f"Average processing time: {avg_time:.2f} seconds")
        
        domains = {}
        for result in successful_queries:
            domain = result['classification']['domain']
            domains[domain] = domains.get(domain, 0) + 1
        
        print("\nDomain distribution:")
        for domain, count in domains.items():
            print(f"  {domain}: {count} queries")
        
        total_articles = sum(r['scraped_articles'] for r in successful_queries)
        print(f"Total articles scraped: {total_articles}")
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"demo_results_{timestamp}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Demo results saved to: {filename}")
    print("\n🎉 Demo completed successfully!")

if __name__ == "__main__":
    # Run the demo
    try:
        asyncio.run(run_demo())
    except KeyboardInterrupt:
        print("\n⚠️ Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        logger.error(f"Demo failed: {e}")

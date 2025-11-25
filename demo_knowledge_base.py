"""
Demo script for knowledge base functionality
Demonstrates using scraped data as knowledge base for answering queries
"""

import asyncio
import json
import os
from agents.classifier_agent import ClassifierAgent
from agents.websearch_agent import WebSearchAgent
from agents.response_agent import ResponseAgent
from agents.utils import load_scraped_data, get_latest_scraped_file

async def demo_knowledge_base():
    """Demo the knowledge base functionality"""
    
    print("🚀 KNOWLEDGE BASE DEMO")
    print("=" * 60)
    print("This demo shows how to use scraped data as a knowledge base")
    print("=" * 60)
    
    # Initialize agents
    classifier = ClassifierAgent()
    websearch = WebSearchAgent()
    response = ResponseAgent()
    
    # Check for existing scraped data
    latest_file = get_latest_scraped_file()
    
    if latest_file:
        print(f"\n📁 Found existing scraped data: {latest_file}")
        
        # Load the scraped data
        scraped_data = load_scraped_data(latest_file)
        
        if scraped_data and 'articles' in scraped_data:
            articles = scraped_data['articles']
            print(f"✅ Loaded {len(articles)} articles from knowledge base")
            
            # Show knowledge base summary
            print(f"\n📚 Knowledge Base Summary:")
            print(f"   Original Query: {scraped_data['metadata']['query']}")
            print(f"   Domain: {scraped_data['metadata']['domain']}")
            print(f"   Total Content: {scraped_data['metadata']['total_content_length']} characters")
            
            # Demo queries
            demo_queries = [
                "What are the latest developments in autonomous drone navigation systems?",
                "Tell me about autonomous systems",
                "What information do you have about drones?",
                "How do navigation systems work?"
            ]
            
            print(f"\n🔍 Demo Queries:")
            print("=" * 60)
            
            for i, query in enumerate(demo_queries, 1):
                print(f"\n📝 Demo Query {i}: {query}")
                print("-" * 50)
                
                try:
                    # Classify the query
                    classification = await classifier.classify_domain(query)
                    print(f"🎯 Classification: {classification['domain']}")
                    print(f"📝 Context: {classification.get('context', 'N/A')}")
                    print(f"🔑 Keywords: {classification['keywords']}")
                    
                    # Generate response using knowledge base
                    print(f"\n🤖 Generating response using knowledge base...")
                    response_text = await response.generate_response(
                        query=query,
                        domain=classification['domain'],
                        keywords=classification['keywords'],
                        scraped_data=articles
                    )
                    
                    print(f"\n💬 Response:")
                    print(response_text)
                    print("-" * 50)
                    
                except Exception as e:
                    print(f"❌ Error: {e}")
            
            print(f"\n" + "=" * 60)
            print("🎉 KNOWLEDGE BASE DEMO COMPLETED")
            
        else:
            print("❌ No articles found in scraped data")
    else:
        print("\n📁 No existing scraped data found")
        print("💡 To create knowledge base data:")
        print("   1. Run the main system to scrape some data")
        print("   2. Or use the websearch agent directly")
        print("   3. Then run this demo again")
        
        # Show how to create new knowledge base
        print(f"\n🔧 Creating new knowledge base...")
        
        # Example query
        query = "What are the latest developments in AI and robotics?"
        
        try:
            # Classify query
            classification = await classifier.classify_domain(query)
            print(f"🎯 Classified as: {classification['domain']}")
            
            # Search and scrape
            print(f"🌐 Searching and scraping content...")
            scraped_data = await websearch.search_and_scrape(
                query=query,
                keywords=classification['keywords'],
                domain=classification['domain']
            )
            
            if scraped_data:
                print(f"✅ Scraped {len(scraped_data)} articles")
                
                # Generate response
                print(f"🤖 Generating response...")
                response_text = await response.generate_response(
                    query=query,
                    domain=classification['domain'],
                    keywords=classification['keywords'],
                    scraped_data=scraped_data
                )
                
                print(f"\n💬 Response:")
                print(response_text)
                
            else:
                print("❌ No articles were scraped")
                
        except Exception as e:
            print(f"❌ Error creating knowledge base: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(demo_knowledge_base())
    except KeyboardInterrupt:
        print("\n⚠️ Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")

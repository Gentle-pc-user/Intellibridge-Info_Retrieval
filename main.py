"""
Multi-Agent System with Streamlit Interface
Main orchestrator for the AI-Robotics/Geopolitics classification and response system
"""

try:
    import streamlit as st
    _HAS_STREAMLIT = True
except ImportError:
    st = None
    _HAS_STREAMLIT = False
import asyncio
import sys
import os
import argparse
import json
from datetime import datetime
from typing import Dict, List, Tuple

from agents.keywords_agent import KeywordsGeneratorAgent
from agents.websearch_agent import WebSearchAgent
from agents.response_agent import ResponseAgent
from agents.utils import setup_logging, clean_text
from config import DEFAULT_CONFIG

# Setup logging
logger = setup_logging()

class MultiAgentSystem:
    """Main orchestrator for the multi-agent system"""
    
    def __init__(self):
        model_name = DEFAULT_CONFIG.LLM_MODEL_NAME
        self.keywords_generator = KeywordsGeneratorAgent(model_name=model_name)
        self.websearch = WebSearchAgent()
        self.response = ResponseAgent(llm_model_name=model_name)
        
    async def process_query(self, user_query: str) -> Dict:
        """
        Process user query through the multi-agent pipeline
        
        Args:
            user_query: User's input query
            
        Returns:
            Dict containing domain, keywords, scraped data, and final response
        """
        try:
            # Step 1: Extract keywords
            logger.info(f"Processing query: {user_query}")
            keywords_result = await self.keywords_generator.extract_keywords(user_query)
            
            keywords = keywords_result.get('keywords', [])
            confidence = keywords_result.get('confidence', 0.0)
            
            logger.info(f"Keywords: {keywords} (confidence: {confidence:.2f})")
            
            # Step 2: Search and scrape relevant content
            scraped_data = []
            # Infer domain for better search prompts
            ai_terms = {"ai", "artificial intelligence", "machine learning", "ml", "deep learning", "gpt", "openai"}
            query_lower = user_query.lower()
            kws_lower = {k.lower() for k in keywords}
            inferred_domain = "ai-robotics" if (ai_terms & kws_lower) or any(t in query_lower for t in ai_terms) else "out-of-domain"
            if keywords:
                scraped_data = await self.websearch.search_and_scrape(
                    query=user_query,
                    keywords=keywords,
                    domain=inferred_domain
                )
            
            # Step 3: Generate response directly with scraped data
            final_response = await self.response.generate_response_with_scraped_data(
                query=user_query,
                keywords=keywords,
                scraped_data=scraped_data
            )
            
            return {
                'keywords': keywords,
                'keywords_confidence': confidence,
                'scraped_articles': len(scraped_data),
                'scraped_data': scraped_data,  # Store scraped data for UI display
                'response': final_response,
                'timestamp': datetime.now().isoformat(),
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            try:
                fallback_response = await self.response._direct_generate(user_query)
            except Exception:
                fallback_response = self.response._generate_fallback_response(user_query)
            return {
                'keywords': [],
                'keywords_confidence': 0.0,
                'scraped_articles': 0,
                'scraped_data': [],
                'response': fallback_response,
                'timestamp': datetime.now().isoformat(),
                'success': False
            }

def create_streamlit_interface():
    """Create the Streamlit web interface"""
    
    st.set_page_config(
        page_title="Intellibridge - AI Query Processing",
        page_icon="📋",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS for white background and blue color scheme
    st.markdown("""
    <style>
    /* White background theme */
    .stApp {
        background: #ffffff;
    }
    
    .main-header {
        font-size: 3.5rem;
        background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 50%, #60a5fa 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 1rem;
        font-weight: bold;
    }
    
    .subtitle {
        font-size: 1.2rem;
        color: #64748b;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .metric-card {
        background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 4px 15px rgba(59, 130, 246, 0.2);
        margin: 0.5rem 0;
        border: 1px solid #e0e7ff;
    }
    
    .query-box {
        background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
        padding: 2rem;
        border-radius: 20px;
        box-shadow: 0 8px 25px rgba(59, 130, 246, 0.15);
        margin: 1rem 0;
        border: 2px solid #dbeafe;
    }
    
    .stats-box {
        background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 4px 15px rgba(59, 130, 246, 0.1);
        border: 1px solid #e2e8f0;
    }
    
    .stats-box h2 {
        color: #1e3a8a !important;
    }
    
    .query-box h2 {
        color: #1e3a8a !important;
    }
    
    .feature-card {
        background: #ffffff;
        padding: 1rem;
        border-radius: 10px;
        border: 1px solid #e2e8f0;
        margin: 0.5rem 0;
        transition: all 0.3s ease;
        color: #000000;
    }
    
    .feature-card strong {
        color: #000000;
    }
    
    .feature-card:hover {
        box-shadow: 0 4px 15px rgba(59, 130, 246, 0.2);
        transform: translateY(-2px);
    }
    
    .icon-container {
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 0.5rem 0;
        gap: 0.5rem;
    }
    
    .icon-img {
        width: 40px;
        height: 40px;
        border-radius: 8px;
    }
    
    .main-icon {
        width: 60px;
        height: 60px;
        border-radius: 12px;
    }
    
    .icon-container h1,
    .icon-container h2 {
        margin: 0;
        color: #1e3a8a;
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background: #f8fafc;
    }
    
    /* Sidebar text colors */
    .css-1d391kg h1, .css-1d391kg h2, .css-1d391kg h3 {
        color: #000000 !important;
    }
    
    .css-1d391kg p, .css-1d391kg span, .css-1d391kg div {
        color: #000000 !important;
    }
    
    /* Button styling */
    .stButton > button {
        background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%);
        color: white;
        border: none;
        border-radius: 10px;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        background: linear-gradient(90deg, #1e40af 0%, #2563eb 100%);
        transform: translateY(-1px);
        box-shadow: 0 4px 15px rgba(59, 130, 246, 0.3);
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        background: #f1f5f9;
        border-radius: 10px;
        padding: 0.5rem;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: #ffffff;
        border-radius: 8px;
        color: #1e3a8a;
        font-weight: 600;
    }
    
    /* General text styling */
    h1, h2, h3, h4, h5, h6 {
        color: #000000 !important;
    }
    
    p, span, div {
        color: #000000 !important;
    }
    
    /* Override for specific headers */
    .main-header {
        color: transparent !important;
    }
    
    .subtitle {
        color: #64748b !important;
    }
    
    /* Metric styling */
    div[data-testid="metric-container"] {
        background: linear-gradient(135deg, #ffffff 0%, #f0f9ff 100%);
        border: 1px solid #dbeafe;
        border-radius: 10px;
        padding: 1rem;
        box-shadow: 0 2px 8px rgba(59, 130, 246, 0.1);
    }
    
    /* Input styling */
    .stTextArea > div > textarea {
        background: #ffffff;
        border: 2px solid #dbeafe;
        border-radius: 10px;
    }
    
    .stTextArea > div > textarea:focus {
        border-color: #3b82f6;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Beautiful Header
    col_header1, col_header2, col_header3 = st.columns([1, 2, 1])
    with col_header2:
        st.markdown('<h1 class="main-header">Intellibridge</h1>', unsafe_allow_html=True)
        st.markdown('<p class="subtitle" style="text-align: center;">Intelligent Query Processing with Advanced Keyword Extraction & Knowledge Base Integration</p>', unsafe_allow_html=True)
    
    # Sidebar with beautiful styling
    with st.sidebar:
        col_icon, col_text = st.columns([1, 3])
        with col_icon:
            st.image("assets/images/system_status_icon.png", width=40)
        with col_text:
            st.markdown('<h2 style="color: white; margin: 0;">System Status</h2>', unsafe_allow_html=True)
        
        # System status with beautiful styling
        if 'system' in st.session_state:
            st.markdown('<div class="metric-card">System Ready<br/>Agents Initialized</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="metric-card">Initializing System...</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        col_icon, col_text = st.columns([1, 3])
        with col_icon:
            st.image("assets/images/feature_icon.png", width=40)
        with col_text:
            st.markdown('<h2 style="color: white; margin: 0;">Features</h2>', unsafe_allow_html=True)
        st.markdown("""
        <div class="feature-card">
            <strong>Smart Keywords Extraction</strong><br/>
            Advanced AI-powered keyword identification
        </div>
        <div class="feature-card">
            <strong>Automated Web Search</strong><br/>
            Real-time content discovery and scraping
        </div>
        <div class="feature-card">
            <strong>Knowledge Base Integration</strong><br/>
            Intelligent information synthesis
        </div>
        <div class="feature-card">
            <strong>AI-Powered Responses</strong><br/>
            Context-aware answer generation
        </div>
        <div class="feature-card">
            <strong>Real-time Processing</strong><br/>
            Fast and efficient query handling
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        col_icon, col_text = st.columns([1, 3])
        with col_icon:
            st.image("assets/images/process_flow_icon.png", width=40)
        with col_text:
            st.markdown('<h2 style="color: white; margin: 0;">Process Flow</h2>', unsafe_allow_html=True)
        st.markdown("""
        <div class="feature-card">
            <strong>1. Extract</strong> relevant keywords
        </div>
        <div class="feature-card">
            <strong>2. Search</strong> recent content
        </div>
        <div class="feature-card">
            <strong>3. Generate</strong> AI response
        </div>
        """, unsafe_allow_html=True)
    
    # Main content area with beautiful layout
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown('<div class="query-box">', unsafe_allow_html=True)
        st.markdown("## Ask Your Question")
        
        # Enhanced query input
        user_query = st.text_area(
            "Enter your question:",
            placeholder="e.g., What are the latest developments in autonomous drone navigation systems?",
            height=120,
            help="Ask any question and our AI will extract relevant keywords, search for information, and provide a comprehensive answer."
        )
        
        # Beautiful process button
        col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
        with col_btn2:
            if st.button("Process Query", type="primary", use_container_width=True):
                if user_query.strip():
                    with st.spinner("Processing your query..."):
                        # Initialize system if needed
                        if 'system' not in st.session_state:
                            st.session_state.system = MultiAgentSystem()
                        
                        # Process query
                        result = asyncio.run(st.session_state.system.process_query(user_query))
                        
                        # Store result in session state
                        st.session_state.last_result = result
                else:
                    st.warning("Please enter a question!")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="stats-box">', unsafe_allow_html=True)
        col_icon, col_text = st.columns([1, 3])
        with col_icon:
            st.image("assets/images/quick_stats_icon.png", width=40)
        with col_text:
            st.markdown('<h2 style="color: white; margin: 0;">Quick Stats</h2>', unsafe_allow_html=True)
        
        if 'last_result' in st.session_state:
            result = st.session_state.last_result
            st.metric("Keywords", len(result['keywords']))
            st.metric("Confidence", f"{result.get('keywords_confidence', 0):.2f}")
            st.metric("Articles", result['scraped_articles'])
            st.metric("Status", "Success" if result['success'] else "Failed")
        else:
            st.info("Process a query to see stats")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Results section with beautiful styling
    if 'last_result' in st.session_state:
        result = st.session_state.last_result
        
        st.markdown("---")
        st.markdown('<h2 style="text-align: center; color: #1e3a8a; margin: 2rem 0;">Results</h2>', unsafe_allow_html=True)
        
        # Tabs for different result sections
        tab1, tab2, tab3, tab4 = st.tabs(["AI Response", "Keywords Analysis", "Processing Details", "Scraped Data"])
        
        with tab1:
            st.markdown("### Final Response")
            if result['success']:
                st.success("Query processed successfully!")
                
                # Display full response in a scrollable container
                st.markdown("""
                <div style="
                    background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
                    color: white;
                    padding: 2rem;
                    border-radius: 15px;
                    box-shadow: 0 4px 15px rgba(30, 58, 138, 0.2);
                    margin: 1rem 0;
                    max-height: 600px;
                    overflow-y: auto;
                    white-space: pre-wrap;
                    word-wrap: break-word;
                ">
                """, unsafe_allow_html=True)
                
                # Display the full response
                st.markdown(result['response'])
                
                st.markdown("</div>", unsafe_allow_html=True)
                
                # Also display in a text area for better readability
                st.markdown("### 📝 Full Response (Scrollable)")
                st.text_area(
                    "Complete Response",
                    result['response'],
                    height=400,
                    disabled=True,
                    label_visibility="collapsed"
                )
                
                # Download option for the response
                st.markdown("### 💾 Download Response")
                response_data = {
                    "query": user_query,
                    "response": result['response'],
                    "keywords": result['keywords'],
                    "keywords_confidence": result['keywords_confidence'],
                    "scraped_articles": result['scraped_articles'],
                    "timestamp": result['timestamp']
                }
                
                response_json = json.dumps(response_data, indent=2)
                st.download_button(
                    label="Download Response as JSON",
                    data=response_json,
                    file_name=f"response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
            else:
                st.error("Processing failed")
                st.markdown(result['response'])
        
        with tab2:
            st.markdown("### Keywords Analysis")
            
            # Beautiful metrics layout
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Keywords Extracted", len(result['keywords']))
            
            with col2:
                st.metric("Confidence Score", f"{result.get('keywords_confidence', 0):.2f}")
            
            with col3:
                st.metric("Articles Found", result['scraped_articles'])
            
            if result.get('keywords'):
                st.markdown("### Extracted Keywords")
                # Beautiful keyword badges
                keyword_html = ""
                for keyword in result['keywords']:
                    keyword_html += f'<span style="background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%); color: white; padding: 0.5rem 1rem; margin: 0.25rem; border-radius: 20px; display: inline-block; font-weight: bold; box-shadow: 0 2px 8px rgba(30, 58, 138, 0.2);">{keyword}</span>'
                
                st.markdown(f'<div style="margin: 1rem 0;">{keyword_html}</div>', unsafe_allow_html=True)
        
        with tab3:
            st.markdown("### Processing Details")
            
            # Beautiful metrics grid
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Articles Found", result['scraped_articles'])
                
            with col2:
                st.metric("Processing Time", "Real-time")
                
            with col3:
                st.metric("Keywords Extracted", len(result['keywords']))
                
            with col4:
                st.metric("Success Rate", "100%" if result['success'] else "0%")
            
            # Technical details in a beautiful card
            st.markdown("### Technical Details")
            details = {
                "timestamp": result['timestamp'],
                "success": result['success'],
                "keywords_count": len(result['keywords']),
                "articles_scraped": result['scraped_articles'],
                "keywords_confidence": result.get('keywords_confidence', 0.0)
            }
            
            # Beautiful JSON display
            st.markdown(f"""
            <div style="
                background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
                color: #1e3a8a;
                padding: 1.5rem;
                border-radius: 15px;
                box-shadow: 0 4px 15px rgba(59, 130, 246, 0.15);
                margin: 1rem 0;
                border: 1px solid #dbeafe;
            ">
                <pre style="color: #1e3a8a; font-family: monospace; white-space: pre-wrap;">{details}</pre>
            </div>
            """, unsafe_allow_html=True)
            
            # Status indicator with beautiful styling
            if result['success']:
                st.markdown("""
                <div style="
                    background: linear-gradient(135deg, #10b981 0%, #059669 100%);
                    color: white;
                    padding: 1rem;
                    border-radius: 10px;
                    text-align: center;
                    font-weight: bold;
                    margin: 1rem 0;
                    box-shadow: 0 4px 15px rgba(16, 185, 129, 0.2);
                ">
                    Query processed successfully!
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div style="
                    background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
                    color: white;
                    padding: 1rem;
                    border-radius: 10px;
                    text-align: center;
                    font-weight: bold;
                    margin: 1rem 0;
                    box-shadow: 0 4px 15px rgba(239, 68, 68, 0.2);
                ">
                    Processing failed
                </div>
                """, unsafe_allow_html=True)
        
        with tab4:
            st.markdown("### Scraped Data")
            
            if result.get('scraped_data') and len(result['scraped_data']) > 0:
                st.success(f"Found {len(result['scraped_data'])} scraped articles")
                
                # Display each scraped article
                for i, article in enumerate(result['scraped_data'], 1):
                    with st.expander(f"Article {i}: {article.get('title', 'Untitled')[:60]}...", expanded=False):
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            st.markdown(f"**Title:** {article.get('title', 'N/A')}")
                            st.markdown(f"**URL:** [{article.get('url', 'N/A')}]({article.get('url', '#')})")
                            st.markdown(f"**Domain:** {article.get('domain', 'N/A')}")
                            
                        with col2:
                            st.markdown(f"**Author:** {article.get('author', 'N/A')}")
                            st.markdown(f"**Date:** {article.get('date_published', 'N/A')}")
                            st.markdown(f"**Length:** {len(article.get('content', ''))} chars")
                        
                        # Content preview
                        content = article.get('content', '')
                        if content:
                            st.markdown("**Content Preview:**")
                            # Show first 500 characters
                            preview = content[:500] + "..." if len(content) > 500 else content
                            st.text_area("Content Preview", preview, height=150, disabled=True, key=f"content_{i}", label_visibility="collapsed")
                        
                        # Keywords used for this article
                        if article.get('keywords'):
                            st.markdown("**Keywords:**")
                            keyword_badges = ""
                            for keyword in article['keywords']:
                                keyword_badges += f'<span style="background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%); color: white; padding: 0.25rem 0.5rem; margin: 0.1rem; border-radius: 10px; display: inline-block; font-size: 0.8rem; box-shadow: 0 2px 8px rgba(30, 58, 138, 0.2);">{keyword}</span>'
                            st.markdown(f'<div style="margin: 0.5rem 0;">{keyword_badges}</div>', unsafe_allow_html=True)
            else:
                st.warning("No scraped data available for this query")
                st.info("Try asking a question to see scraped articles here")

def main():
    """Main entry point with mode selection"""
    parser = argparse.ArgumentParser(description='Intellibridge Multi-Agent System')
    parser.add_argument('--mode', choices=['streamlit', 'flask'], default='streamlit',
                       help='Choose interface mode: streamlit (default) or flask')
    args = parser.parse_args()
    
    # Setup logging
    os.makedirs("logs", exist_ok=True)
    
    try:
        import streamlit as st
        _HAS_STREAMLIT = True
    except ImportError:
        _HAS_STREAMLIT = False

    if args.mode == 'flask':
        # Import and run Flask app
        try:
            from flask_app import app
            print(" Starting Intellibridge Flask Server...")
            print(" Web Interface: http://localhost:5000")
            print(" API Endpoint: http://localhost:5000/api/query")
            print(" Health Check: http://localhost:5000/api/health")
            app.run(host='0.0.0.0', port=5000, debug=True)
        except ImportError as e:
            print(f" Flask import error: {e}")
            print("Please install Flask: pip install flask flask-cors")
            sys.exit(1)
    else:
        # Default Streamlit mode
        if not _HAS_STREAMLIT:
            print(" Streamlit is not installed. Install it with 'pip install streamlit' or run with '--mode flask'.")
            sys.exit(1)
        create_streamlit_interface()

if __name__ == "__main__":
    main()

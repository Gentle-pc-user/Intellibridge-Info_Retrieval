# 🚀 Multi-Agent System - Project Overview

## 📋 Project Summary

This is a sophisticated multi-agent system that provides real-time domain-specific information retrieval and response generation. The system specializes in **AI-Robotics** and **Geopolitics** domains using advanced LLM and RAG technologies.

## 🏗️ System Architecture

```
User Query → ClassifierAgent → WebSearchAgent → ResponseAgent → Final Response
     ↓              ↓               ↓              ↓
Domain + Keywords → Recent Content → Vector Store → RAG/Direct Response
```

### Agent Components

1. **ClassifierAgent** (`agents/classifier_agent.py`)
   - Uses Gemma 3 for domain classification
   - Extracts relevant keywords
   - Few-shot prompting for accuracy

2. **WebSearchAgent** (`agents/websearch_agent.py`)
   - DuckDuckGo Search integration
   - BeautifulSoup web scraping
   - Quality filtering and content extraction

3. **ResponseAgent** (`agents/response_agent.py`)
   - FAISS vector store for embeddings
   - RAG pipeline for contextual responses
   - Gemma 3 integration for generation

## 📁 File Structure

```
├── main.py                     # Streamlit web interface
├── demo.py                     # Demo script with sample queries
├── run.py                      # Startup script
├── test_installation.py        # Installation verification
├── config.py                   # Configuration management
├── requirements.txt            # Python dependencies
├── README.md                   # Comprehensive documentation
├── PROJECT_OVERVIEW.md         # This file
├── agents/                     # Agent implementations
│   ├── __init__.py
│   ├── classifier_agent.py     # Domain classification
│   ├── websearch_agent.py      # Web search & scraping
│   ├── response_agent.py       # RAG pipeline
│   ├── prompt.py               # Structured prompts
│   └── utils.py                # Shared utilities
├── data/                       # Data storage
│   ├── scraped/               # Scraped articles
│   └── embeddings/            # FAISS indices
└── logs/                      # System logs
    └── multi_agent.log        # Application logs
```

## 🚀 Quick Start

### 1. Installation
```bash
# Install dependencies
pip install -r requirements.txt

# Test installation
python test_installation.py
```

### 2. Run the System
```bash
# Start Streamlit web interface
python run.py app
# or
streamlit run main.py

# Run demo with sample queries
python run.py demo
```

### 3. Access the Interface
- Open your browser to `http://localhost:8501`
- Enter queries related to AI-Robotics or Geopolitics
- View real-time processing and results

## 🎯 Key Features

### Domain Classification
- **AI-Robotics**: Autonomous systems, machine learning, robotics, computer vision
- **Geopolitics**: International relations, political conflicts, diplomatic affairs
- **Out-of-Domain**: General queries outside specialization

### Web Search & Scraping
- Recent content retrieval (last 24 hours)
- Trusted domain prioritization
- Quality content filtering
- Respectful rate limiting

### Response Generation
- **RAG Pipeline**: For substantial content (>3000 chars)
- **Direct Generation**: For limited content
- Contextual, evidence-based responses
- Source attribution

## 🔧 Configuration

### Model Settings
- **LLM**: Gemma 3 (2B/9B parameters)
- **Embeddings**: sentence-transformers/all-MiniLM-L6-v2
- **Vector Store**: FAISS with cosine similarity

### Performance Tuning
- Adjust search result counts in `config.py`
- Modify chunk sizes for RAG pipeline
- Configure concurrent request limits

## 📊 Performance Metrics

### Typical Performance (RTX 3080)
- **Classification**: 2-3 seconds
- **Web Search**: 5-10 seconds  
- **Response Generation**: 3-5 seconds
- **Total Pipeline**: 10-18 seconds

### Memory Requirements
- **GPU Memory**: 4-8GB (model dependent)
- **RAM**: 2-4GB
- **Disk Space**: 1-2GB (models + data)

## 🧪 Testing

### Installation Test
```bash
python test_installation.py
```

### Demo Queries
```bash
python demo.py
```

### Sample Queries
- "What are the latest developments in autonomous drone navigation?"
- "How is AI being used in robotic surgery?"
- "What are the implications of China's Belt and Road Initiative?"
- "How are trade tensions between US and China evolving?"

## 🔍 Monitoring

### Log Files
- `logs/multi_agent.log`: Complete system logs
- Real-time processing updates
- Error tracking and debugging

### Metrics Tracked
- Query classification accuracy
- Search result quality
- Scraping success rates
- Response generation time
- Vector store performance

## 🛠️ Development

### Adding New Domains
1. Update `ClassifierPrompts` in `agents/prompt.py`
2. Add domain-specific search strategies
3. Update trusted domains list

### Customizing Models
1. Modify model names in `config.py`
2. Update prompt templates
3. Adjust embedding strategies

### Extending Functionality
1. Add new agents in `agents/` directory
2. Update main orchestration in `main.py`
3. Extend Streamlit interface

## 🔒 Security & Ethics

### Content Safety
- Input validation and sanitization
- Rate limiting for web scraping
- Respectful content extraction
- Error handling and graceful failures

### Privacy Considerations
- No user data storage
- Temporary processing only
- Secure web scraping practices
- No personal information collection

## 📈 Future Enhancements

### Planned Features
- Multi-language support
- Advanced caching mechanisms
- Real-time news feeds integration
- Enhanced domain coverage
- Performance optimizations

### Scalability Improvements
- Distributed processing
- Load balancing
- Database integration
- API endpoints

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Implement changes
4. Add tests
5. Submit pull request

## 📄 License

MIT License - see LICENSE file for details.

## 🙏 Acknowledgments

- **Google**: Gemma 3 model
- **Hugging Face**: Transformers library
- **FAISS**: Vector search
- **DuckDuckGo**: Search API
- **Streamlit**: Web interface

---

**Built with ❤️ for intelligent information retrieval**

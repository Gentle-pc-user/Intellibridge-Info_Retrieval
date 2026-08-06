<div align = "center">
     <img src =  "templates/Images/Intellibridge_banner.png" alt = "Intllibridge_banner" width = 100%>
</div>
* # Multi-Agent System for Domain-Specific Information Retrieval

A sophisticated multi-agent system that provides real-time domain-specific information retrieval and response generation for **AI-Robotics** and **Geopolitics** domains using advanced LLM and RAG technologies.

* ## Features

- **Domain Classification**: Automatically classifies queries into AI-Robotics, Geopolitics, or Out-of-Domain
- **Real-time Web Search**: Uses DuckDuckGo Search for recent, authoritative content
- **Intelligent Scraping**: BeautifulSoup-based content extraction with quality filtering
- **RAG Pipeline**: FAISS vector store with sentence-transformers for contextual retrieval
- **Ollama Integration**: Local Gemma 3 model via Ollama for response generation
- **Streamlit Interface**: User-friendly web interface for interaction
- **Async Processing**: High-performance concurrent operations

* ## Architecture

```
User Query → ClassifierAgent → WebSearchAgent → ResponseAgent → Final Response
     ↓              ↓               ↓              ↓
Domain + Keywords → Recent Content → Vector Store → RAG/Direct Response
```

* ### Agent Workflow

1. **ClassifierAgent**: Uses Ollama Gemma 3 with few-shot prompting to classify domain and extract keywords
2. **WebSearchAgent**: Searches recent content using DDGS, scrapes with BeautifulSoup
3. **ResponseAgent**: Builds FAISS index, retrieves relevant content, generates contextual responses via Ollama

* ## Installation

* ### Prerequisites

- Python 3.8+
- Ollama installed and running
- 8GB+ RAM (16GB+ recommended)
- Internet connection for initial model download

* ### Setup

1. **Install Ollama**
```bash
# Download and install Ollama from: https://ollama.ai/download
# Then start the Ollama server:
ollama serve
```

2. **Clone the repository**
```bash
git clone <repository-url>
cd multi-agent-system
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Setup Ollama model**
```bash
python setup_ollama.py
```

5. **Test installation**
```bash
python test_installation.py
```

* ## Usage

* ### Running the Streamlit App

```bash
streamlit run main.py
```

The app will be available at `http://localhost:8501`

* ### Example Queries

**AI-Robotics Domain:**
- "What are the latest developments in autonomous drone navigation systems?"
- "How is AI being used in robotic surgery?"
- "What are the newest breakthroughs in computer vision?"

**Geopolitics Domain:**
- "How is the Russia-Ukraine conflict affecting global energy markets?"
- "What are the implications of China's Belt and Road Initiative?"
- "How are trade tensions between US and China evolving?"

* ## Configuration

* ### Model Configuration

Edit the agent initialization in `main.py`:

```python
# For different Ollama models
classifier = ClassifierAgent(model_name="gemma2:latest")      # Default Gemma 2
classifier = ClassifierAgent(model_name="gemma2:2b")          # Smaller Gemma 2B
classifier = ClassifierAgent(model_name="gemma2:9b")          # Larger Gemma 9B
```

* ### Search Configuration

Modify `agents/websearch_agent.py`:

```python
# Adjust search parameters
max_results_per_query = 10      # Search results per query
max_scrape_per_query = 5        # Articles to scrape per query
```

* ### RAG Configuration

Modify `agents/response_agent.py`:

```python
# Adjust RAG parameters
chunk_size = 1000               # Text chunk size
chunk_overlap = 200             # Overlap between chunks
large_threshold = 3000          # Use RAG if content > this length
```

* ## Project Structure

```
├── main.py                     # Streamlit app entry point
├── requirements.txt            # Python dependencies
├── README.md                  # This file
├── agents/                    # Agent implementations
│   ├── __init__.py
│   ├── classifier_agent.py    # Domain classification
│   ├── websearch_agent.py     # Web search & scraping
│   ├── response_agent.py      # RAG pipeline
│   ├── prompt.py              # Structured prompts
│   └── utils.py               # Shared utilities
├── data/                      # Data storage
│   ├── scraped/              # Scraped articles
│   └── embeddings/           # FAISS indices
└── logs/                     # Log files
    └── multi_agent.log       # System logs
```

* ## Technical Details

### Models Used

- **LLM**: Ollama Gemma 2 (latest/2B/9B) for classification and generation
- **Embeddings**: sentence-transformers/all-MiniLM-L6-v2
- **Vector Store**: FAISS with cosine similarity
- **Search**: DuckDuckGo Search API
- **Scraping**: BeautifulSoup + fake-useragent

### Performance Optimizations

- **Async Processing**: Concurrent web scraping and model inference
- **Caching**: FAISS index persistence across sessions
- **Quality Filtering**: Trusted domain prioritization
- **Content Chunking**: Efficient text processing for embeddings
- **Rate Limiting**: Respectful web scraping with delays

### Memory Management

- **Local Processing**: Ollama handles model memory management
- **Text Chunking**: Prevents memory overflow with large documents
- **Index Optimization**: Efficient FAISS operations

* ## Monitoring & Logging

### Log Files

- `logs/multi_agent.log`: Complete system logs
- `logs/recent_scraper.log`: Web scraping logs (from reference)

### Metrics Tracked

- Query classification accuracy
- Search result quality
- Scraping success rates
- Response generation time
- Vector store performance

* ## Troubleshooting

### Common Issues

1. **Ollama Connection Issues**
   - Ensure Ollama is running: `ollama serve`
   - Check if model is installed: `ollama list`
   - Install required model: `ollama pull gemma2:latest`

2. **Web Scraping Failures**
   - Check internet connection
   - Verify target websites are accessible
   - Adjust rate limiting

3. **Slow Performance**
   - Use smaller Ollama models (gemma2:2b instead of gemma2:9b)
   - Reduce search result counts
   - Optimize chunk sizes

### Debug Mode

Enable detailed logging:

```python
import logging
logging.getLogger().setLevel(logging.DEBUG)
```

* ## Security Considerations

- **Input Validation**: All user queries are validated
- **Rate Limiting**: Respectful web scraping practices
- **Content Filtering**: Removes potentially harmful content
- **Error Handling**: Graceful failure modes

* ## Performance Benchmarks

### Typical Performance (Local Ollama)

- **Classification**: ~2-4 seconds
- **Web Search**: ~5-10 seconds
- **Response Generation**: ~3-6 seconds
- **Total Pipeline**: ~10-20 seconds

### Memory Usage

- **RAM Usage**: ~8-16GB (depending on model size)
- **Disk Space**: ~4-8GB (for Ollama models and data)
- **CPU/GPU**: Ollama handles resource management

* ## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

* ## License

This project is licensed under the MIT License - see the LICENSE file for details.

* ## Acknowledgments

- **Google**: For the Gemma 3 model
- **Hugging Face**: For the transformers library
- **FAISS**: For efficient vector search
- **DuckDuckGo**: For search API
- **Streamlit**: For the web interface

* ## Support

For issues and questions:

1. Check the troubleshooting section
2. Review the logs in `logs/multi_agent.log`
3. Create an issue in the repository
4. Contact the development team

---

**Built with ❤️ for intelligent information retrieval**
=======
# Intellibridge-Info_Retrieval
Capstone project 
>>>>>>> 7b9c18d87b67e2139bb1d1c6fe9d59bf9267544b

# Flask Integration for Intellibridge

This document explains how to use the Flask integration with the existing Streamlit-based Intellibridge system.

## Overview

The system now supports **both** Streamlit and Flask interfaces:

- **Streamlit**: Original interface with rich UI components
- **Flask**: Web API with simple HTML interface + REST endpoints

## Installation

```bash
pip install flask flask-cors
```

## Running the System

### Option 1: Streamlit (Default)

```bash
python main.py
# or
python main.py --mode streamlit
# or
streamlit run main.py
```

### Option 2: Flask Mode

```bash
python main.py --mode flask
# or
python run_flask.py
```

## Flask Endpoints

### Web Interface

- **URL**: http://localhost:5000
- **Features**: Simple web form for queries with real-time responses

### API Endpoints

#### Process Query

- **POST** `/api/query`
- **Body**: `{"query": "your question here"}`
- **Response**:

```json
{
  "response": "Generated answer...",
  "metadata": {
    "processing_time": 3.2,
    "timestamp": "2025-11-19T17:26:00",
    "domain": "general",
    "keywords": ["keyword1", "keyword2"],
    "sources_count": 5,
    "success": true
  }
}
```

#### Health Check

- **GET** `/api/health`
- **Response**: System status and timestamp

#### System Stats

- **GET** `/api/stats`
- **Response**: System information and components

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Flask App      │    │  MultiAgent     │
│                 │    │                  │    │  System         │
│ • Streamlit UI  │◄──►│ • HTTP Routes    │◄──►│ • Keywords       │
│ • Flask HTML    │    │ • API Endpoints  │    │ • Web Search     │
│ • REST Clients  │    │ • CORS Support   │    │ • Response Gen   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Usage Examples

### Using the Web Interface

1. Navigate to http://localhost:5000
2. Enter your query in the text box
3. Click "Process Query"
4. View results with metadata

### Using the API

```bash
curl -X POST http://localhost:5000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the latest developments in AI?"}'
```

```python
import requests

response = requests.post(
    'http://localhost:5000/api/query',
    json={'query': 'current prime minister of Japan'}
)
result = response.json()
print(result['response'])
```

## Benefits of Flask Integration

1. **API Access**: Programmatic access to the system
2. **Cross-platform**: Works with any HTTP client
3. **Integration**: Easy to integrate with other systems
4. **Deployment**: Can be deployed on any web server
5. **Scalability**: Can be scaled with standard web techniques

## Files Added/Modified

- `flask_app.py` - Main Flask application
- `run_flask.py` - Quick Flask launcher
- `main.py` - Updated with mode selection
- `requirements.txt` - Added Flask dependencies

## Troubleshooting

### Import Errors

```bash
pip install flask flask-cors
```

### NumPy Compatibility Issues

If you encounter NumPy compatibility errors:

```bash
pip install "numpy<2"
```

### Port Conflicts

Change port in `flask_app.py`:

```python
app.run(host='0.0.0.0', port=5001, debug=True)
```

## Next Steps

- Add authentication for API endpoints
- Implement rate limiting
- Add database persistence for queries
- Create Docker configuration
- Add unit tests for Flask endpoints

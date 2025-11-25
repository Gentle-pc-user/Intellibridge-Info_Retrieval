from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import asyncio
import sys
import os
import json
from datetime import datetime
from threading import Lock

# Add the current directory to Python path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import MultiAgentSystem

app = Flask(__name__)
CORS(app)

# Initialize the MultiAgentSystem
agent_system = MultiAgentSystem()
process_lock = Lock()

@app.route('/')
def index():
    """Serve the main web interface"""
    return render_template('index.html')

@app.route('/api/query', methods=['POST'])
def process_query():
    """API endpoint to process queries"""
    try:
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({'error': 'Missing query parameter'}), 400
        
        query = data['query'].strip()
        if not query:
            return jsonify({'error': 'Empty query'}), 400
        
        # Process the query using the existing MultiAgentSystem (serialized to avoid memory spikes)
        start_time = datetime.now()
        with process_lock:
            result = asyncio.run(agent_system.process_query(query))
        end_time = datetime.now()
        
        # Format the response for the rich UI
        response_data = {
            'response': result.get('response', 'No response generated'),
            'keywords': result.get('keywords', []),
            'keywords_confidence': result.get('keywords_confidence', 0.0),
            'scraped_articles': result.get('scraped_articles', 0),
            'scraped_data': result.get('scraped_data', []),
            'success': result.get('success', False),
            'timestamp': result.get('timestamp', end_time.isoformat()),
            'metadata': {
                'processing_time': (end_time - start_time).total_seconds(),
                'timestamp': end_time.isoformat(),
                'domain': result.get('domain'),
                'keywords': result.get('keywords', []),
                'sources_count': result.get('scraped_articles', 0),
                'success': result.get('success', False)
            }
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })

@app.route('/api/stats')
def get_stats():
    """Get system statistics"""
    try:
        # You can expand this with actual system stats
        return jsonify({
            'system': 'Intellibridge Multi-Agent System',
            'status': 'running',
            'components': ['Keyword Extraction', 'Web Search', 'Content Scraping', 'Response Generation'],
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("🚀 Starting Intellibridge Flask Server...")
    print("📱 Web Interface: http://localhost:5000")
    print("🔗 API Endpoint: http://localhost:5000/api/query")
    print("💚 Health Check: http://localhost:5000/api/health")
    
    app.run(host='0.0.0.0', port=5000, debug=True)

#!/usr/bin/env python3
"""
Quick launcher for Flask mode
"""

import subprocess
import sys
import os

def main():
    """Run Flask app directly"""
    print("🚀 Starting Intellibridge Flask Server...")
    print("📱 Web Interface: http://localhost:5000")
    print("🔗 API Endpoint: http://localhost:5000/api/query")
    print("💚 Health Check: http://localhost:5000/api/health")
    print("\n💡 Use Ctrl+C to stop the server")
    
    try:
        # Run the Flask app directly
        from flask_app import app
        app.run(host='0.0.0.0', port=5000, debug=True)
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Please install required packages: pip install flask flask-cors")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")

if __name__ == "__main__":
    main()

"""
Startup script for the Multi-Agent System
Provides easy commands to run different components of the system
"""

import sys
import subprocess
import os
from typing import List

def run_streamlit_app():
    """Run the Streamlit web interface"""
    print("🚀 Starting Multi-Agent System Streamlit App...")
    try:
        subprocess.run([sys.executable, "-m", "streamlit", "run", "main.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to start Streamlit app: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⚠️ Streamlit app stopped by user")

def run_demo():
    """Run the demo script"""
    print("🎯 Running Multi-Agent System Demo...")
    try:
        subprocess.run([sys.executable, "demo.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Demo failed: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⚠️ Demo stopped by user")

def run_installation_test():
    """Run the installation test"""
    print("🔍 Running Installation Test...")
    try:
        subprocess.run([sys.executable, "test_installation.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Installation test failed: {e}")
        sys.exit(1)

def install_requirements():
    """Install required packages"""
    print("📦 Installing required packages...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
        print("✅ Requirements installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install requirements: {e}")
        sys.exit(1)

def show_help():
    """Show help message"""
    print("""
🤖 Multi-Agent System - Startup Script

Usage: python run.py [command]

Commands:
    app         Start the Streamlit web interface (default)
    demo        Run the demo script with sample queries
    test        Run installation test to verify setup
    install     Install required packages from requirements.txt
    help        Show this help message

Examples:
    python run.py          # Start the Streamlit app
    python run.py app      # Start the Streamlit app
    python run.py demo     # Run the demo
    python run.py test     # Test installation
    python run.py install  # Install requirements

For more information, see README.md
""")

def main():
    """Main function to handle command line arguments"""
    
    # Get command from arguments
    command = sys.argv[1] if len(sys.argv) > 1 else "app"
    
    # Ensure we're in the right directory
    if not os.path.exists("main.py"):
        print("❌ Error: main.py not found. Please run this script from the project root directory.")
        sys.exit(1)
    
    # Handle commands
    commands = {
        "app": run_streamlit_app,
        "demo": run_demo,
        "test": run_installation_test,
        "install": install_requirements,
        "help": show_help
    }
    
    if command in commands:
        commands[command]()
    else:
        print(f"❌ Unknown command: {command}")
        print("Use 'python run.py help' to see available commands")
        sys.exit(1)

if __name__ == "__main__":
    main()

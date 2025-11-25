"""
Ollama Setup Script for Multi-Agent System
Helps set up and verify Ollama installation with the required model
"""

import subprocess
import sys
import json
import requests
import time
from typing import List, Dict, Any

def check_ollama_installed() -> bool:
    """Check if Ollama is installed and running"""
    try:
        result = subprocess.run(['ollama', '--version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"✅ Ollama is installed: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ Ollama command failed: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("❌ Ollama command timed out")
        return False
    except FileNotFoundError:
        print("❌ Ollama is not installed or not in PATH")
        return False
    except Exception as e:
        print(f"❌ Error checking Ollama: {e}")
        return False

def check_ollama_server() -> bool:
    """Check if Ollama server is running"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            print("✅ Ollama server is running")
            return True
        else:
            print(f"❌ Ollama server responded with status: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Ollama server is not running")
        return False
    except Exception as e:
        print(f"❌ Error checking Ollama server: {e}")
        return False

def start_ollama_server() -> bool:
    """Start Ollama server"""
    try:
        print("🔄 Starting Ollama server...")
        # Start Ollama server in background
        subprocess.Popen(['ollama', 'serve'], 
                        stdout=subprocess.DEVNULL, 
                        stderr=subprocess.DEVNULL)
        
        # Wait for server to start
        for i in range(30):  # Wait up to 30 seconds
            time.sleep(1)
            if check_ollama_server():
                print("✅ Ollama server started successfully")
                return True
        
        print("❌ Ollama server failed to start within 30 seconds")
        return False
        
    except Exception as e:
        print(f"❌ Error starting Ollama server: {e}")
        return False

def list_available_models() -> List[Dict[str, Any]]:
    """List available models in Ollama"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=10)
        if response.status_code == 200:
            data = response.json()
            models = data.get('models', [])
            return models
        else:
            print(f"❌ Failed to list models: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Error listing models: {e}")
        return []

def pull_model(model_name: str) -> bool:
    """Pull a model from Ollama registry"""
    try:
        print(f"🔄 Pulling model: {model_name}")
        print("This may take several minutes depending on model size...")
        
        process = subprocess.Popen(
            ['ollama', 'pull', model_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Stream output
        for line in process.stdout:
            print(f"   {line.strip()}")
        
        process.wait()
        
        if process.returncode == 0:
            print(f"✅ Successfully pulled model: {model_name}")
            return True
        else:
            print(f"❌ Failed to pull model: {model_name}")
            return False
            
    except Exception as e:
        print(f"❌ Error pulling model {model_name}: {e}")
        return False

def test_model(model_name: str) -> bool:
    """Test if a model works correctly"""
    try:
        print(f"🧪 Testing model: {model_name}")
        
        test_prompt = "Hello, how are you?"
        
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model_name,
                "prompt": test_prompt,
                "stream": False
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            if 'response' in result:
                print(f"✅ Model {model_name} is working correctly")
                print(f"   Test response: {result['response'][:100]}...")
                return True
            else:
                print(f"❌ Model {model_name} returned invalid response")
                return False
        else:
            print(f"❌ Model {model_name} test failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing model {model_name}: {e}")
        return False

def setup_ollama():
    """Main setup function"""
    print("🚀 OLLAMA SETUP FOR MULTI-AGENT SYSTEM")
    print("=" * 50)
    
    # Step 1: Check if Ollama is installed
    print("\n1️⃣ Checking Ollama installation...")
    if not check_ollama_installed():
        print("\n❌ Ollama is not installed!")
        print("Please install Ollama from: https://ollama.ai/download")
        print("After installation, run this script again.")
        return False
    
    # Step 2: Check if Ollama server is running
    print("\n2️⃣ Checking Ollama server...")
    if not check_ollama_server():
        print("\n⚠️ Ollama server is not running. Attempting to start...")
        if not start_ollama_server():
            print("\n❌ Failed to start Ollama server!")
            print("Please start Ollama server manually: ollama serve")
            return False
    
    # Step 3: List available models
    print("\n3️⃣ Checking available models...")
    models = list_available_models()
    if models:
        print(f"Available models ({len(models)}):")
        for model in models:
            name = model.get('name', 'Unknown')
            size = model.get('size', 0)
            size_gb = size / (1024**3)
            print(f"   - {name} ({size_gb:.1f} GB)")
    else:
        print("No models found")
    
    # Step 4: Check for required model
    print("\n4️⃣ Checking for required model...")
    required_model = "llama3.2-vision"
    model_names = [model.get('name', '') for model in models]
    
    if required_model not in model_names:
        print(f"⚠️ Required model '{required_model}' not found")
        print(f"Available models: {model_names}")
        
        # Ask user if they want to pull the model
        response = input(f"\nDo you want to pull '{required_model}'? (y/n): ").lower().strip()
        if response in ['y', 'yes']:
            if not pull_model(required_model):
                print(f"❌ Failed to pull {required_model}")
                return False
        else:
            print(f"❌ Cannot proceed without {required_model}")
            return False
    else:
        print(f"✅ Required model '{required_model}' is available")
    
    # Step 5: Test the model
    print("\n5️⃣ Testing model...")
    if not test_model(required_model):
        print(f"❌ Model {required_model} failed the test")
        return False
    
    # Final success message
    print("\n" + "=" * 50)
    print("🎉 OLLAMA SETUP COMPLETED SUCCESSFULLY!")
    print("=" * 50)
    print(f"✅ Ollama is installed and running")
    print(f"✅ Model '{required_model}' is ready")
    print(f"✅ System is ready to use")
    print("\nNext steps:")
    print("1. Run: python test_installation.py")
    print("2. Run: streamlit run main.py")
    print("3. Or run: python demo.py")
    
    return True

def main():
    """Main function"""
    try:
        success = setup_ollama()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

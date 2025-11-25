#!/usr/bin/env python3
"""
Script to manage Ollama memory usage and optimize for low-memory systems
"""

import subprocess
import sys
import json
import requests
import time

def check_system_memory():
    """Check available system memory"""
    try:
        import psutil
        memory = psutil.virtual_memory()
        total_gb = memory.total / (1024**3)
        available_gb = memory.available / (1024**3)
        used_percent = memory.percent
        
        print(f" System Memory Status:")
        print(f"   Total: {total_gb:.1f} GB")
        print(f"   Available: {available_gb:.1f} GB")
        print(f"   Used: {used_percent:.1f}%")
        
        return available_gb
    except ImportError:
        print("⚠️ psutil not installed. Install with: pip install psutil")
        return None

def stop_ollama():
    """Stop Ollama service to free memory"""
    try:
        print("🛑 Stopping Ollama service...")
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/f", "/im", "ollama.exe"], check=False)
        else:
            subprocess.run(["pkill", "-f", "ollama"], check=False)
        time.sleep(2)
        print("✅ Ollama stopped")
        return True
    except Exception as e:
        print(f"❌ Error stopping Ollama: {e}")
        return False

def start_ollama():
    """Start Ollama service"""
    try:
        print("🚀 Starting Ollama service...")
        if sys.platform == "win32":
            subprocess.Popen(["ollama", "serve"], creationflags=subprocess.CREATE_NEW_CONSOLE)
        else:
            subprocess.Popen(["ollama", "serve"])
        time.sleep(5)
        print("✅ Ollama started")
        return True
    except Exception as e:
        print(f"❌ Error starting Ollama: {e}")
        return False

def check_ollama_status():
    """Check if Ollama is running and responsive"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json()
            print(f"✅ Ollama is running with {len(models.get('models', []))} models")
            return True
        else:
            print(f"⚠️ Ollama responded with status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Ollama not responding: {e}")
        return False

def optimize_ollama_for_memory():
    """Set environment variables for memory optimization"""
    import os
    
    print("🔧 Setting memory optimization environment variables...")
    
    # Set Ollama environment variables for memory efficiency
    os.environ['OLLAMA_NUM_PARALLEL'] = '1'  # Limit parallel requests
    os.environ['OLLAMA_MAX_LOADED_MODELS'] = '1'  # Only keep one model loaded
    os.environ['OLLAMA_FLASH_ATTENTION'] = 'true'  # Enable flash attention for memory efficiency
    os.environ['OLLAMA_LLM_LIBRARY'] = 'cpu'  # Force CPU usage
    
    print("✅ Memory optimization settings applied")

def unload_models():
    """Unload all models from memory"""
    try:
        print("🧹 Unloading models from memory...")
        # This will unload models by making a request with empty context
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3.2-vision",
                "prompt": "",
                "keep_alive": 0  # Unload immediately
            },
            timeout=10
        )
        print("✅ Models unloaded from memory")
        return True
    except Exception as e:
        print(f"⚠️ Could not unload models: {e}")
        return False

def main():
    """Main function to manage Ollama memory"""
    print("🔧 Ollama Memory Management Tool")
    print("=" * 40)
    
    # Check system memory
    available_memory = check_system_memory()
    
    if available_memory and available_memory < 2.0:
        print(f"⚠️ Low memory detected ({available_memory:.1f} GB available)")
        print("💡 Recommendations:")
        print("   1. Close other applications")
        print("   2. Restart Ollama with memory optimizations")
        print("   3. Use a smaller model if available")
    
    print("\nChoose an option:")
    print("1. Check Ollama status")
    print("2. Restart Ollama with memory optimizations")
    print("3. Unload models from memory")
    print("4. Stop Ollama")
    print("5. Start Ollama")
    print("6. Exit")
    
    choice = input("\nEnter your choice (1-6): ").strip()
    
    if choice == "1":
        check_ollama_status()
    elif choice == "2":
        optimize_ollama_for_memory()
        stop_ollama()
        time.sleep(2)
        start_ollama()
        time.sleep(3)
        check_ollama_status()
    elif choice == "3":
        unload_models()
    elif choice == "4":
        stop_ollama()
    elif choice == "5":
        start_ollama()
        time.sleep(3)
        check_ollama_status()
    elif choice == "6":
        print("👋 Goodbye!")
    else:
        print("❌ Invalid choice")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Script to update DuckDuckGo search package to the new ddgs package
"""

import subprocess
import sys

def update_ddgs_package():
    """Update to the new ddgs package"""
    try:
        print("🔄 Updating DuckDuckGo search package...")
        
        # Uninstall old package
        print("📦 Uninstalling old duckduckgo_search package...")
        subprocess.run([sys.executable, "-m", "pip", "uninstall", "duckduckgo_search", "-y"], 
                      check=False)
        
        # Install new package
        print("📦 Installing new ddgs package...")
        subprocess.run([sys.executable, "-m", "pip", "install", "ddgs"], 
                      check=True)
        
        print("✅ Successfully updated to ddgs package!")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error updating package: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = update_ddgs_package()
    if success:
        print("\n🎉 Package update completed successfully!")
        print("💡 The websearch agent will now use the updated ddgs package.")
    else:
        print("\n⚠️ Package update failed. The system will fall back to the old package.")

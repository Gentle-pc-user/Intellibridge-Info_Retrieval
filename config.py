"""
Configuration settings for the application.

This file contains configuration settings and API keys.
For security reasons, never commit this file with actual credentials.
Instead, use environment variables or a .env file.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# API Keys (Load from environment variables)
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', 'your_openai_api_key_here')
# Add other API keys as needed
# EXAMPLE_API_KEY = os.getenv('EXAMPLE_API_KEY', 'your_example_api_key_here')

# Application Settings
DEBUG = os.getenv('DEBUG', 'False').lower() in ('true', '1', 't')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Add other configuration settings as needed
# DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///app.db')

# Example configuration class (uncomment and modify as needed)
"""
class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
"""

# Add any additional configuration classes or settings below

if __name__ == "__main__":
    # This block runs when the script is executed directly
    print("Current configuration:")
    for key, value in globals().items():
        if key.isupper() and not key.startswith('_'):
            print(f"{key}: {value}")

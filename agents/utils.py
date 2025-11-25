import os
import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

def setup_logging(log_file: str = "logs/multi_agent.log") -> logging.Logger:
    """
    Setup logging configuration for the multi-agent system
    
    Args:
        log_file: Path to log file
        
    Returns:
        Configured logger instance
    """
    # Create logs directory if it doesn't exist
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info("Logging system initialized")
    return logger

def clean_text(text: str, max_length: int = 8000) -> str:
    """
    Clean and normalize text content
    
    Args:
        text: Raw text to clean
        max_length: Maximum length of cleaned text
        
    Returns:
        Cleaned text
    """
    if not text:
        return ""
    
    # Remove extra whitespace and newlines
    text = re.sub(r'\s+', ' ', text.strip())
    
    # Remove special characters but keep basic punctuation
    text = re.sub(r'[^\w\s\.\,\!\?\:\;\-\(\)]', '', text)
    
    # Limit length
    if len(text) > max_length:
        text = text[:max_length] + "..."
    
    return text

def clean_filename(text: str) -> str:
    """
    Clean text for use in filenames
    
    Args:
        text: Text to clean
        
    Returns:
        Cleaned filename-safe text
    """
    if not text:
        return "untitled"
    
    # Remove invalid filename characters
    text = re.sub(r'[\\/*?:"<>|]', "", text)
    
    # Replace spaces with underscores
    text = re.sub(r'\s+', '_', text)
    
    # Limit length
    return text[:100] if text else "untitled"

def save_json(data: Dict[str, Any], filepath: str) -> bool:
    """
    Save data to JSON file
    
    Args:
        data: Data to save
        filepath: Path to save file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return True
    except Exception as e:
        logging.error(f"Failed to save JSON to {filepath}: {e}")
        return False

def load_json(filepath: str) -> Optional[Dict[str, Any]]:
    """
    Load data from JSON file
    
    Args:
        filepath: Path to JSON file
        
    Returns:
        Loaded data or None if failed
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Failed to load JSON from {filepath}: {e}")
        return None

def extract_domain_from_url(url: str) -> str:
    """
    Extract domain from URL
    
    Args:
        url: URL to extract domain from
        
    Returns:
        Domain name
    """
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.netloc.replace('www.', '')
    except:
        return "unknown"

def is_recent_date(date_str: str, days_back: int = 7) -> bool:
    """
    Check if date is within recent timeframe
    
    Args:
        date_str: Date string to check
        days_back: Number of days back to consider recent
        
    Returns:
        True if date is recent
    """
    try:
        from dateutil.parser import parse as parse_date
        from datetime import timedelta
        
        parsed_date = parse_date(date_str).date()
        cutoff_date = datetime.now().date() - timedelta(days=days_back)
        return parsed_date >= cutoff_date
    except:
        return True  # If can't parse, assume recent

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """
    Split text into overlapping chunks for embedding
    
    Args:
        text: Text to chunk
        chunk_size: Size of each chunk
        overlap: Overlap between chunks
        
    Returns:
        List of text chunks
    """
    if not text or len(text) <= chunk_size:
        return [text] if text else []
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # Try to break at sentence boundary
        if end < len(text):
            # Look for sentence endings within the last 100 characters
            search_start = max(start + chunk_size - 100, start)
            sentence_end = text.rfind('.', search_start, end)
            if sentence_end > start:
                end = sentence_end + 1
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        start = end - overlap
        
        if start >= len(text):
            break
    
    return chunks

def format_timestamp() -> str:
    """
    Get current timestamp in ISO format
    
    Returns:
        ISO formatted timestamp
    """
    return datetime.now().isoformat()

def validate_query(query: str) -> bool:
    """
    Validate user query
    
    Args:
        query: User query to validate
        
    Returns:
        True if query is valid
    """
    if not query or not query.strip():
        return False
    
    # Check minimum length
    if len(query.strip()) < 3:
        return False
    
    # Check for suspicious patterns
    suspicious_patterns = ['<script>', 'javascript:', 'eval(', 'exec(']
    query_lower = query.lower()
    
    for pattern in suspicious_patterns:
        if pattern in query_lower:
            return False
    
    return True

def load_scraped_data(filepath: str) -> Optional[Dict[str, Any]]:
    """
    Load scraped data from JSON file
    
    Args:
        filepath: Path to scraped data JSON file
        
    Returns:
        Loaded scraped data or None if failed
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"✅ Loaded scraped data from {filepath}")
        return data
        
    except Exception as e:
        print(f"❌ Failed to load scraped data from {filepath}: {e}")
        return None

def get_latest_scraped_file(scraped_dir: str = "data/scraped") -> Optional[str]:
    """
    Get the most recent scraped data file
    
    Args:
        scraped_dir: Directory containing scraped files
        
    Returns:
        Path to latest scraped file or None if not found
    """
    try:
        if not os.path.exists(scraped_dir):
            return None
        
        # Get all JSON files in scraped directory
        json_files = [f for f in os.listdir(scraped_dir) if f.endswith('.json')]
        
        if not json_files:
            return None
        
        # Sort by modification time (newest first)
        json_files.sort(key=lambda x: os.path.getmtime(os.path.join(scraped_dir, x)), reverse=True)
        
        latest_file = os.path.join(scraped_dir, json_files[0])
        print(f"✅ Found latest scraped file: {latest_file}")
        
        return latest_file
        
    except Exception as e:
        print(f"❌ Error finding latest scraped file: {e}")
        return None

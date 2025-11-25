# Memory Management Fixes for Ollama LLM

## Problem Identified
The system was failing with memory errors:
```
ERROR - Error generating LLM response with Ollama: model requires more system memory (3.8 GiB) than is available (3.0 GiB)
```

The websearch agent was working perfectly (successfully scraping 2025-specific articles), but the LLM couldn't generate responses due to insufficient memory.

## Solutions Implemented

### 1. **Memory-Efficient LLM Settings**
Reduced memory usage in `_generate_with_llm()`:
```python
# Before
'num_predict': 512,
'num_ctx': 1024,
'num_thread': 2,

# After  
'num_predict': 256,    # Reduced response length
'num_ctx': 512,        # Smaller context window
'num_thread': 1,       # Single thread
'num_gpu': 0,          # Force CPU usage
'low_vram': True,      # Enable low VRAM mode
```

### 2. **Aggressive Content Truncation**
Reduced scraped content size:
```python
# Before
if len(content) > 2000:
    content = content[:2000] + "..."

# After
if len(content) > 800:
    content = content[:800] + "..."
```

### 3. **Memory-Efficient Fallback Method**
Added `_generate_memory_efficient_response()`:
- Uses only first 2 sources (instead of all 5)
- Limits each source to 200 characters
- Ultra-conservative LLM settings:
  - `num_predict`: 150 (very short responses)
  - `num_ctx`: 256 (minimal context)
  - Single thread, CPU-only

### 4. **Scraped Data Fallback**
Added `_create_basic_response_from_scraped_data()`:
- When LLM completely fails, still uses scraped web content
- Extracts key sentences from articles
- Creates structured response with sources
- Ensures users get recent web information even with memory constraints

### 5. **Ollama Memory Management Tool**
Created `manage_ollama_memory.py`:
- Check system memory status
- Restart Ollama with memory optimizations
- Unload models from memory
- Set memory-efficient environment variables

## Memory Optimization Strategy

### Automatic Fallback Chain:
1. **Normal LLM Generation** → If memory error →
2. **Memory-Efficient LLM** → If still fails →
3. **Basic Scraped Data Response** → Always works

### Environment Variables for Ollama:
```bash
OLLAMA_NUM_PARALLEL=1
OLLAMA_MAX_LOADED_MODELS=1
OLLAMA_FLASH_ATTENTION=true
OLLAMA_LLM_LIBRARY=cpu
```

## Expected Results

### Before Fix:
- ❌ Memory error → Generic fallback response
- ❌ No use of scraped web content
- ❌ Users get outdated information

### After Fix:
- ✅ Memory-efficient LLM generation
- ✅ Scraped data used even when LLM fails
- ✅ Users always get recent web information
- ✅ Graceful degradation under memory constraints

## Usage Instructions

### For Immediate Relief:
1. Run `python manage_ollama_memory.py`
2. Choose option 2: "Restart Ollama with memory optimizations"

### For Persistent Issues:
1. Close other memory-intensive applications
2. Restart your system to free memory
3. Use the memory management tool regularly

### System Requirements:
- **Minimum**: 3 GB available RAM
- **Recommended**: 4+ GB available RAM
- **Optimal**: 8+ GB total system RAM

The system now ensures that even with severe memory constraints, users will receive responses based on recent web content rather than generic fallbacks.

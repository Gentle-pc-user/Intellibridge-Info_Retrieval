# Recency-Based Article Selection Improvements

## Problem Identified
The system was scraping articles but not prioritizing the most recent ones. When users asked about "2025 technologies," the system would return articles from 2024 or earlier years, even though more recent articles were available.

## Root Cause Analysis
1. **Sequential Selection**: The system was taking the first `MAX_SCRAPE_PER_QUERY * 2` results without considering recency
2. **Basic Sorting**: Articles were sorted only by relevance score and content length, not by publication date
3. **No Year Detection**: Search queries didn't prioritize the specific year mentioned in the user's query

## Solutions Implemented

### 1. **Smart Query Generation** (`_generate_search_queries`)
- **Year Detection**: Automatically detects years mentioned in queries (e.g., "2025")
- **Year-Specific Queries**: Generates targeted search queries with the detected year
- **Fallback to Current Year**: If no year is mentioned, uses current year for recent results
- **More Query Variations**: Increased from 8 to 10 search queries for better coverage

### 2. **Recency-Based Prioritization** (`_prioritize_by_recency`)
- **Year-Based Scoring**: Articles mentioning the query year get highest priority (score +10.0)
- **Current Year Boost**: Articles from current year get high priority (score +8.0)
- **Recent Indicators**: Boost for terms like "latest", "new", "breaking", "announced" (+4.0 to +8.0)
- **Old Year Penalties**: Articles from 2022 and earlier get penalized (-3.0)
- **Detailed Logging**: Shows top 5 prioritized results with scores for debugging

### 3. **Date-Based Final Sorting** (`_get_date_score`)
- **Publication Date Priority**: Articles sorted by actual publication date first
- **Recency Scoring**: 
  - Last 30 days: 970-1000 points
  - Last 3 months: 780-900 points  
  - Last year: 562-700 points
  - Older: 0-500 points
- **Fallback Handling**: Graceful handling of unparseable dates

### 4. **Enhanced Search Strategy**
- **Multiple Time Limits**: Tries month, week, day, and all-time searches if initial searches return no results
- **Increased Search Results**: `MAX_RESULTS_PER_QUERY` increased from 10 to 15
- **Better Selection Pool**: Scrapes from top 15 results (3x `MAX_SCRAPE_PER_QUERY`) instead of 10

### 5. **Comprehensive Logging**
- **Search Prioritization**: Shows which articles got highest recency scores
- **Final Selection**: Displays the final 5 articles selected with their publication dates
- **Year Detection**: Logs when specific years are detected in queries

## Configuration Changes

### Before:
```python
MAX_RESULTS_PER_QUERY = 10
MAX_SCRAPE_PER_QUERY = 5
```

### After:
```python
MAX_RESULTS_PER_QUERY = 15  # More results for better selection
MAX_SCRAPE_PER_QUERY = 5    # Same final count, but most recent ones
```

## How It Works Now

1. **Query Analysis**: System detects if user mentions a specific year (e.g., "2025")
2. **Targeted Search**: Generates search queries specifically targeting that year
3. **Result Scoring**: Each search result gets a recency score based on title/snippet content
4. **Smart Selection**: Selects top 15 results for scraping (instead of first 10)
5. **Date-Based Sorting**: Final articles sorted by actual publication date
6. **Recent First**: Returns the 5 most recent, relevant articles

## Expected Improvements

- ✅ **Year-Specific Results**: When asking about "2025 technologies", get 2025 articles
- ✅ **Recency Priority**: Most recent articles appear first
- ✅ **Better Search Coverage**: More search queries with year-specific terms
- ✅ **Intelligent Selection**: Smart prioritization instead of sequential selection
- ✅ **Detailed Logging**: Better visibility into the selection process

## Testing Recommendations

Test with queries like:
- "What are the new technologies developed in 2025?"
- "Latest AI advancements in 2024"
- "Recent robotics breakthroughs"
- "Emerging technologies 2025"

The system should now prioritize articles from the mentioned year and show clear logging of the selection process.

# RAG Workflow Documentation

## Complete Workflow from Start to Finish

### 1. User Query Input

```
User asks: "Who is the current Prime Minister of Japan?"
```

### 2. Response Generation Initiation

```
generate_response() called with:
- query: "Who is the current Prime Minister of Japan?"
- keywords: ["japan", "prime minister", "economic"]
- scraped_data: List of 3 articles
```

### 3. RAG Workflow Activation

```
Using 3 scraped articles with RAG workflow
Starting RAG workflow...
```

### 4. Embedding Model Initialization

```
Initializing embedding model...
Loading embedding model: all-MiniLM-L6-v2
Embedding model loaded successfully
```

### 5. FAISS Index Initialization

```
Initializing FAISS index...
FAISS index initialized with dimension: 384
```

### 6. Previous Index Cleanup

```
Clearing previous index...
Index cleared successfully
```

### 7. Document Processing and Embedding

```
Adding 3 documents to FAISS index...
Batches: 100%|██████████████| 1/1 [00:00<00:00, 99.22it/s]
Generating embeddings for 3 chunks
Batches: 100%|██████████████| 1/1 [00:00<00:00, 53.64it/s]
Added 3 chunks to index
Index saved successfully
```

### 8. Vector Search for Relevant Documents

```
Retrieving relevant documents using vector search...
Batches: 100%|██████████████| 1/1 [00:00<00:00, 99.99it/s]
Retrieved 3 relevant documents
Retrieved 3 relevant documents
```

### 9. RAG Response Generation

```
Generating response using RAG...
Starting LLM generation - no timeout, will wait as long as needed...
```

### 10. LLM Processing (if memory available)

```
HTTP Request: POST http://localhost:11434/api/generate
[LLM processes the RAG prompt with retrieved context]
```

### 11. Final Response Output

```
Response generated successfully
[Final response returned to user]
```

---

## Detailed Logging Activity

### Phase 1: Initialization

```log
2025-11-17 17:58:45,244 - agents.utils - INFO - Generating response for query: Who is the current Prime Minister of Japan?...
2025-11-17 17:58:45,244 - agents.utils - INFO - Using 3 scraped articles with RAG workflow
2025-11-17 17:58:45,244 - agents.utils - INFO - Starting RAG workflow...
```

### Phase 2: Model Loading

```log
2025-11-17 17:58:45,244 - agents.utils - INFO - Initializing embedding model...
2025-11-17 17:58:45,244 - agents.utils - INFO - Loading embedding model: all-MiniLM-L6-v2
2025-11-17 17:58:45,264 - agents.utils - INFO - Embedding model loaded successfully
```

### Phase 3: Index Management

```log
2025-11-17 17:58:45,244 - agents.utils - INFO - Clearing previous index...
2025-11-17 17:58:45,249 - agents.utils - INFO - Index cleared successfully
2025-11-17 17:58:45,250 - agents.utils - INFO - Adding 3 documents to FAISS index...
2025-11-17 17:58:45,264 - agents.utils - INFO - FAISS index initialized with dimension: 384
```

### Phase 4: Document Embedding

```log
2025-11-17 17:58:45,264 - agents.utils - INFO - Generating embeddings for 3 chunks
Batches: 100%|██████████████| 1/1 [00:00<00:00, 53.64it/s]
2025-11-17 17:58:45,287 - agents.utils - INFO - Added 3 chunks to index
2025-11-17 17:58:45,290 - agents.utils - INFO - Index saved successfully
```

### Phase 5: Vector Search

```log
2025-11-17 17:58:45,290 - agents.utils - INFO - Retrieving relevant documents using vector search...
Batches: 100%|██████████████| 1/1 [00:00<00:00, 99.99it/s]
2025-11-17 17:58:45,302 - agents.utils - INFO - Retrieved 3 relevant documents
2025-11-17 17:58:45,303 - agents.utils - INFO - Retrieved 3 relevant documents
```

### Phase 6: LLM Generation

```log
2025-11-17 17:58:45,303 - agents.utils - INFO - Generating response using RAG...
2025-11-17 17:58:45,303 - agents.utils - INFO - Starting LLM generation - no timeout, will wait as long as needed...
2025-11-17 17:58:46,126 - httpx - INFO - HTTP Request: POST http://localhost:11434/api/generate "HTTP/1.1 500 Internal Server Error"
```

### Phase 7: Error Handling (Memory Issue)

```log
2025-11-17 17:58:46,127 - agents.utils - ERROR - Error generating LLM response with Ollama: model requires more system memory (4.9 GiB) than is available (3.5 GiB) (status code: 500)
2025-11-17 17:58:46,127 - agents.utils - INFO - Memory error detected, trying memory-efficient approach...
2025-11-17 17:58:46,127 - agents.utils - INFO - Using minimal prompt (length: 182 chars)
2025-11-17 17:58:46,127 - agents.utils - INFO - Starting memory-efficient LLM generation - no timeout...
```

### Phase 8: Final Output

```log
2025-11-17 17:58:45,244 - agents.utils - INFO - Response generated successfully
Response: **Response:**
System memory constraints are preventing response generation. Please try with a smaller query or restart the system.
Length: 131 characters
```

---

## Workflow Components

### Input Processing

- **Query Validation**: Checks if query is valid
- **Keywords**: Used for post-processing (not in RAG itself)
- **Scraped Data**: List of articles with title, content, URL, source

### Embedding Pipeline

- **Model**: `all-MiniLM-L6-v2` (384 dimensions)
- **Processing**: Documents chunked and embedded
- **Storage**: FAISS IndexFlatIP for cosine similarity

### Vector Search

- **Query Embedding**: User query converted to vector
- **Similarity Search**: Finds top-k most similar documents
- **Retrieval**: Returns relevant documents with metadata

### Response Generation

- **RAG Prompt**: Combines query with retrieved context
- **LLM**: Ollama model generates final response
- **Fallback**: Memory-efficient generation if needed

### Error Handling

- **Graceful Degradation**: Falls back to knowledge base method if RAG fails
- **Memory Management**: Tries smaller prompts if memory constrained
- **Logging**: Comprehensive error tracking and debugging info

---

## Performance Metrics

### Timing (from logs)

- **Embedding Model Load**: ~20ms
- **FAISS Index Init**: ~5ms
- **Document Embedding**: ~30ms (3 documents)
- **Vector Search**: ~10ms
- **Total RAG Pipeline**: ~65ms (excluding LLM)

### Memory Usage

- **Embedding Model**: ~90MB (all-MiniLM-L6-v2)
- **FAISS Index**: Minimal (3 documents)
- **Vector Storage**: 384 dimensions per document chunk

### Throughput

- **Documents Processed**: 3 articles
- **Chunks Created**: 3 chunks (one per article in this case)
- **Embeddings Generated**: 3 embeddings
- **Documents Retrieved**: 3 relevant documents (k=5, but only 3 available)

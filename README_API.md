# Company RAG API

A FastAPI-based Retrieval-Augmented Generation (RAG) system for company websites with conversation history support.

## Features

- 🚀 **FastAPI REST API** with automatic documentation
- 🔍 **Intelligent Document Retrieval** using vector similarity search
- 💬 **Conversation History** with Redis persistence
- 🏢 **Company-focused** crawling of GoGel Real Estate and Uptura Tech websites
- 📊 **Real-time Statistics** and corpus management
- 🐳 **Docker Support** for easy deployment
- 🔒 **User-specific Conversations** with email-based identification

## Quick Start

### 1. Environment Setup

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your configuration
# At minimum, set your OPENAI_API_KEY
```

### 2. Install Dependencies

```bash
# Create virtual environment
python -m venv myenv
source myenv/bin/activate  # On Windows: myenv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

### 3. Start Redis (Required for conversation history)

```bash
# Using Docker
docker run -d -p 6379:6379 redis:7-alpine

# Or using Docker Compose
docker-compose up redis -d
```

### 4. Run the API

```bash
# Development mode
python main.py

# Or using uvicorn directly
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Test the API

```bash
# Run test suite
python test_api.py

# Or visit the interactive docs
# http://localhost:8000/docs
```

## API Endpoints

### 🏗️ Build RAG Corpus
**POST** `/prep-rag`

Build or rebuild the RAG corpus from company websites.

```json
{
  "urls": [
    "https://thebngc.com",
    "https://gogel.thebngc.com",
    "https://uptura-tech.com"
  ],
  "force_rebuild": false
}
```

**Response:**
```json
{
  "message": "RAG corpus built successfully",
  "documents_count": 338,
  "urls_processed": 13,
  "timestamp": "2025-10-30T22:00:00"
}
```

### ❓ Ask Questions
**POST** `/ask`

Ask questions to the RAG system with conversation context.

```json
{
  "query": "What do you know about GoGel?",
  "user_id": "user@gmail.com",
  "max_context_chars": 4000,
  "top_k": 5
}
```

**Response:**
```json
{
  "answer": "GoGel Real Estate is a company with over 15 years of experience...",
  "sources": [
    {
      "score": 0.85,
      "id": "doc_id_123",
      "url": "https://gogel.thebngc.com",
      "text": "GoGel Real Estate has been serving..."
    }
  ],
  "conversation_id": "conv_abc123",
  "timestamp": "2025-10-30T22:00:00"
}
```

### 💬 Conversation History
**GET** `/conversation/{user_id}`

Get conversation history for a specific user.

**DELETE** `/conversation/{user_id}`

Clear conversation history for a specific user.

### 📊 Corpus Statistics
**GET** `/corpus/stats`

Get detailed statistics about the current corpus.

### 🔍 Health Check
**GET** `/`

API health check and status.

## Docker Deployment

### Using Docker Compose (Recommended)

```bash
# Set your environment variables
export OPENAI_API_KEY=your_key_here

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Using Docker Only

```bash
# Start Redis
docker run -d --name redis -p 6379:6379 redis:7-alpine

# Build and run API
docker build -t rag-api .
docker run -d --name rag-api -p 8000:8000 \
  -e OPENAI_API_KEY=your_key_here \
  -e REDIS_URL=redis://redis:6379 \
  --link redis \
  rag-api
```

## Usage Examples

### Building the Corpus

```bash
curl -X POST "http://localhost:8000/prep-rag" \
  -H "Content-Type: application/json" \
  -d '{"force_rebuild": true}'
```

### Asking Questions

```bash
curl -X POST "http://localhost:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What services does GoGel provide?",
    "user_id": "user@example.com"
  }'
```

### Getting Conversation History

```bash
curl "http://localhost:8000/conversation/user@example.com"
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key (required) | - |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379` |
| `API_HOST` | API host address | `0.0.0.0` |
| `API_PORT` | API port | `8000` |

### RAG Configuration

The system uses the same configuration as the local RAG implementation in `rag_website.py`:

- **Chunk Size**: 800 characters
- **Chunk Overlap**: 150 characters
- **Top-K Retrieval**: 5 documents
- **Similarity Threshold**: 0.3
- **Max Pages to Crawl**: 300

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI App   │    │     Redis       │    │    OpenAI       │
│                 │    │                 │    │                 │
│ • REST API      │◄──►│ • Corpus        │    │ • Embeddings    │
│ • Request       │    │ • Conversations │    │ • Chat          │
│   Handling      │    │ • Session Mgmt  │    │   Completions   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  RAG Engine     │    │  Vector Store   │    │   Web Crawler   │
│                 │    │                 │    │                 │
│ • Similarity    │    │ • Document      │    │ • Playwright    │
│   Search        │    │   Embeddings    │    │ • BeautifulSoup │
│ • Context       │    │ • Metadata      │    │ • Content       │
│   Building      │    │ • Retrieval     │    │   Extraction    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Features in Detail

### Conversation History
- **Persistent Storage**: Conversations stored in Redis with 7-day expiration
- **User Isolation**: Each user's conversation is separate
- **Context Awareness**: Recent conversation history is included in queries
- **Message Limit**: Maximum 50 messages per user (configurable)

### Vector Search
- **OpenAI Embeddings**: Uses `text-embedding-3-small` model
- **Cosine Similarity**: Fast similarity calculations
- **Relevance Filtering**: Configurable similarity threshold
- **Source Attribution**: All responses include source URLs and relevance scores

### Content Processing
- **Smart Chunking**: Sentence-boundary aware text splitting
- **Enhanced Crawling**: JavaScript-rendered content via Playwright
- **Metadata Preservation**: URL and context tracking for all documents
- **Error Handling**: Robust error handling and logging

## Development

### Local Development

```bash
# Install in development mode
pip install -e .

# Run with auto-reload
uvicorn main:app --reload

# Run tests
python test_api.py

# Check API documentation
# http://localhost:8000/docs
```

### Testing

The API includes comprehensive testing:

- **Health checks**
- **Corpus building and statistics**
- **Question-answering with conversation context**
- **Conversation history management**

## Monitoring and Logs

### Logging
The API provides structured logging for:
- Request processing
- Corpus operations
- Conversation management
- Error tracking

### Metrics Available
- Corpus size and statistics
- Response times
- User conversation counts
- Error rates

## Troubleshooting

### Common Issues

1. **Redis Connection Failed**
   - Ensure Redis is running on the specified URL
   - Check firewall and network connectivity
   - Conversation history will be disabled if Redis is unavailable

2. **OpenAI API Errors**
   - Verify your API key is valid and has sufficient credits
   - Check rate limits and quotas

3. **Empty Corpus**
   - Run `/prep-rag` endpoint to build the corpus
   - Check that the target websites are accessible
   - Review logs for crawling errors

4. **Poor Question Quality**
   - Ensure the corpus is built with relevant content
   - Check similarity thresholds
   - Review conversation context

### Performance Tips

- Use Redis for better performance and conversation persistence
- Build corpus during off-peak hours
- Monitor OpenAI API usage and costs
- Consider caching frequently asked questions

## License

This project is proprietary software for company use.
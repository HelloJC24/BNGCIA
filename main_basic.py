"""
Minimal FastAPI RAG API Server - Basic version without numpy
For initial testing and deployment debugging
"""
import os
import json
import math
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging

import redis
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
from openai import OpenAI

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize OpenAI client with error handling
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    logger.warning("OPENAI_API_KEY not found in environment variables")
    client = None
else:
    try:
        client = OpenAI(api_key=openai_api_key)
        logger.info("OpenAI client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI client: {e}")
        client = None

# Configuration
EMBEDDING_MODEL = "text-embedding-3-small"
LLM_MODEL = "gpt-4o-mini"
TOP_K = 5
DEFAULT_URLS = [
    "https://thebngc.com",
    "https://gogel.thebngc.com",
    "https://gogel.thebngc.com/agents"
]

# Initialize FastAPI app
app = FastAPI(
    title="Company RAG API - Basic",
    description="Basic RAG system for testing deployment",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Redis
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
try:
    redis_client = redis.from_url(redis_url, decode_responses=True)
    redis_client.ping()
    logger.info(f"Connected to Redis at {redis_url}")
except Exception as e:
    logger.error(f"Failed to connect to Redis: {e}")
    redis_client = None

# Pydantic models
class QueryRequest(BaseModel):
    question: str
    conversation_id: Optional[str] = None
    user_id: Optional[str] = "anonymous"

class PrepRequest(BaseModel):
    urls: Optional[List[str]] = None
    force_rebuild: bool = False

class QueryResponse(BaseModel):
    answer: str
    sources: List[str]
    conversation_id: str
    timestamp: str

class PrepResponse(BaseModel):
    status: str
    documents_processed: int
    message: str

# Simple cosine similarity without numpy
def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Calculate cosine similarity between two vectors without numpy"""
    if len(a) != len(b):
        return 0.0
    
    dot_product = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
    
    return dot_product / (norm_a * norm_b)

def scrape_website(url: str) -> str:
    """Simple web scraping function"""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove script and style elements
        for element in soup(["script", "style"]):
            element.decompose()
        
        # Get text and clean it
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return text[:10000]  # Limit text length
    
    except Exception as e:
        logger.error(f"Error scraping {url}: {e}")
        return ""

def create_chunks(text: str, chunk_size: int = 800, overlap: int = 100) -> List[str]:
    """Split text into overlapping chunks"""
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        
        # Try to break at sentence end
        if end < len(text):
            last_period = chunk.rfind('.')
            if last_period > chunk_size // 2:
                chunk = chunk[:last_period + 1]
                end = start + last_period + 1
        
        chunks.append(chunk.strip())
        start = end - overlap
        
        if start >= len(text):
            break
    
    return chunks

def get_embedding(text: str) -> List[float]:
    """Get embedding for text"""
    if not client:
        logger.error("OpenAI client not initialized")
        return [0.0] * 1536  # Return zero vector
    
    try:
        response = client.embeddings.create(
            input=text,
            model=EMBEDDING_MODEL
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Error getting embedding: {e}")
        return [0.0] * 1536  # Return zero vector

@app.get("/")
async def health_check():
    """Health check endpoint"""
    status = {
        "status": "healthy",
        "redis_connected": redis_client is not None,
        "openai_available": client is not None,
        "timestamp": datetime.now().isoformat()
    }
    
    if redis_client:
        try:
            redis_client.ping()
            status["redis_status"] = "connected"
        except:
            status["redis_status"] = "disconnected"
            status["redis_connected"] = False
    
    return status

@app.post("/prep-rag/", response_model=PrepResponse)
async def prep_rag(request: PrepRequest, background_tasks: BackgroundTasks):
    """Build or rebuild the RAG corpus"""
    if not redis_client:
        raise HTTPException(status_code=500, detail="Redis not available")
    
    urls = request.urls or DEFAULT_URLS
    
    # Check if corpus exists and force_rebuild is False
    if not request.force_rebuild:
        existing_count = redis_client.scard("corpus:documents")
        if existing_count > 0:
            return PrepResponse(
                status="exists",
                documents_processed=existing_count,
                message=f"Corpus already exists with {existing_count} documents. Use force_rebuild=true to rebuild."
            )
    
    def build_corpus():
        documents = []
        doc_id = 0
        
        for url in urls:
            logger.info(f"Processing {url}")
            content = scrape_website(url)
            
            if content:
                chunks = create_chunks(content)
                
                for chunk in chunks:
                    if len(chunk.strip()) > 50:  # Only process meaningful chunks
                        embedding = get_embedding(chunk)
                        
                        doc = {
                            "id": doc_id,
                            "text": chunk,
                            "embedding": embedding,
                            "source": url,
                            "created_at": datetime.now().isoformat()
                        }
                        
                        # Store in Redis
                        redis_client.hset(f"corpus:doc:{doc_id}", mapping={
                            "text": chunk,
                            "embedding": json.dumps(embedding),
                            "source": url,
                            "created_at": doc["created_at"]
                        })
                        
                        redis_client.sadd("corpus:documents", doc_id)
                        doc_id += 1
        
        # Store metadata
        redis_client.hset("corpus:metadata", mapping={
            "total_documents": doc_id,
            "last_updated": datetime.now().isoformat(),
            "urls": json.dumps(urls)
        })
        
        logger.info(f"Corpus built with {doc_id} documents")
        return doc_id
    
    # Run corpus building in background for large datasets
    background_tasks.add_task(build_corpus)
    
    return PrepResponse(
        status="building",
        documents_processed=0,
        message="Corpus building started. Check status with health endpoint."
    )

@app.post("/migrate-corpus")
async def migrate_corpus():
    """Migrate local corpus to Redis"""
    if not redis_client:
        raise HTTPException(status_code=500, detail="Redis not available")
    
    try:
        # Load local corpus
        with open("corpus_local.json", "r", encoding="utf-8") as f:
            local_corpus = json.load(f)
        
        # Clear existing corpus
        doc_ids = redis_client.smembers("corpus:documents")
        for doc_id in doc_ids:
            redis_client.delete(f"corpus:doc:{doc_id}")
        redis_client.delete("corpus:documents")
        redis_client.delete("corpus:metadata")
        
        # Migrate documents
        migrated_count = 0
        for doc in local_corpus:
            doc_id = doc.get("id", migrated_count)
            
            redis_data = {
                "text": doc["text"],
                "embedding": json.dumps(doc["embedding"]),
                "source": doc["source"],
                "created_at": doc.get("created_at", datetime.now().isoformat())
            }
            
            redis_client.hset(f"corpus:doc:{doc_id}", mapping=redis_data)
            redis_client.sadd("corpus:documents", doc_id)
            migrated_count += 1
        
        # Store metadata
        sources = list(set(doc["source"] for doc in local_corpus))
        redis_client.hset("corpus:metadata", mapping={
            "total_documents": migrated_count,
            "last_updated": datetime.now().isoformat(),
            "urls": json.dumps(sources),
            "migration_source": "corpus_local.json"
        })
        
        return {
            "status": "success",
            "documents_migrated": migrated_count,
            "sources": sources,
            "message": f"Successfully migrated {migrated_count} documents from local corpus to Redis"
        }
        
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="corpus_local.json not found")
    except Exception as e:
        logger.error(f"Migration error: {e}")
        raise HTTPException(status_code=500, detail=f"Migration failed: {str(e)}")

@app.post("/debug-search")
async def debug_search(request: QueryRequest):
    """Debug endpoint to see what content is actually retrieved"""
    if not redis_client:
        raise HTTPException(status_code=500, detail="Redis not available")
    
    # Get query embedding
    query_embedding = get_embedding(request.question)
    
    # Retrieve relevant documents
    doc_ids = redis_client.smembers("corpus:documents")
    similarities = []
    
    for doc_id in doc_ids:
        doc_data = redis_client.hgetall(f"corpus:doc:{doc_id}")
        if doc_data:
            doc_embedding = json.loads(doc_data["embedding"])
            similarity = cosine_similarity(query_embedding, doc_embedding)
            similarities.append((similarity, doc_data, doc_id))
    
    # Sort by similarity and get top K
    similarities.sort(key=lambda x: x[0], reverse=True)
    top_docs = similarities[:10]  # Get more for debugging
    
    return {
        "question": request.question,
        "total_documents": len(similarities),
        "top_similarities": [
            {
                "doc_id": doc_id,
                "similarity": similarity,
                "source": doc_data["source"],
                "text_preview": doc_data["text"][:200] + "..." if len(doc_data["text"]) > 200 else doc_data["text"]
            }
            for similarity, doc_data, doc_id in top_docs
        ]
    }

@app.post("/ask", response_model=QueryResponse)
async def ask_question(request: QueryRequest):
    """Query the RAG system"""
    if not redis_client:
        raise HTTPException(status_code=500, detail="Redis not available")
    
    # Check if corpus exists
    doc_count = redis_client.scard("corpus:documents")
    if doc_count == 0:
        raise HTTPException(status_code=404, detail="No corpus found. Please run /prep-rag/ first.")
    
    # Get query embedding
    query_embedding = get_embedding(request.question)
    
    # Retrieve relevant documents
    doc_ids = redis_client.smembers("corpus:documents")
    similarities = []
    
    # Also do a simple text search for names/specific terms
    text_matches = []
    question_words = request.question.lower().split()
    
    for doc_id in doc_ids:
        doc_data = redis_client.hgetall(f"corpus:doc:{doc_id}")
        if doc_data:
            doc_text_lower = doc_data["text"].lower()
            
            # Vector similarity
            doc_embedding = json.loads(doc_data["embedding"])
            similarity = cosine_similarity(query_embedding, doc_embedding)
            similarities.append((similarity, doc_data))
            
            # Text matching - boost documents that contain query terms
            text_match_score = 0
            for word in question_words:
                if len(word) > 2 and word in doc_text_lower:
                    text_match_score += 1
            
            if text_match_score > 0:
                text_matches.append((text_match_score, doc_data))
    
    # Combine and prioritize text matches for specific names/terms
    if text_matches:
        text_matches.sort(key=lambda x: x[0], reverse=True)
        # Add top text matches to similarities with boosted scores
        for score, doc_data in text_matches[:3]:
            similarities.append((0.9 + score * 0.1, doc_data))  # Boost text matches
    
    # Sort by similarity and get top K
    similarities.sort(key=lambda x: x[0], reverse=True)
    top_docs = similarities[:TOP_K]
    
    if not top_docs:
        raise HTTPException(status_code=404, detail="No relevant documents found")
    
    # Prepare context
    context_parts = []
    sources = []
    
    for similarity, doc in top_docs:
        context_parts.append(f"Source: {doc['source']}\nContent: {doc['text']}")
        sources.append(doc['source'])
    
    context = "\n\n".join(context_parts)
    
    # Generate conversation ID
    conversation_id = request.conversation_id or f"conv_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Check if this is a greeting or casual conversation
    question_lower = request.question.lower().strip()
    greeting_words = ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening', 'how are you', 'what\'s up', 'greetings']
    is_greeting = any(greeting in question_lower for greeting in greeting_words) and len(question_lower.split()) <= 3
    
    # Generate answer
    if not client:
        raise HTTPException(status_code=500, detail="OpenAI client not available")
    
    try:
        if is_greeting:
            # Handle greetings with a more conversational prompt
            prompt = f"""You are a helpful assistant named "Rafa" for BNGC company . The user is greeting you or starting a conversation.

Respond naturally to their greeting and introduce yourself. Mention that you can help them learn about BNGC and its services. Be warm and welcoming.

Company context (for reference):
{context[:500]}...

User: {request.question}

Response:"""
        else:
            # Handle information requests with context - ALWAYS use the context for factual questions
            prompt = f"""You are an assistant named "Rafa" for BNGC. Use the provided context to answer questions about the company.

IMPORTANT: The user is asking about specific information. Search through the context carefully.

Guidelines:
- Search the context thoroughly for any mention of what the user is asking about
- If you find relevant information in the context, provide it
- If the specific information isn't in the context, be honest and say "I don't see any mention of [specific thing] in our current information"
- Always try to be helpful and provide what related information you do have
- When user say Thank you or Goodbye, respond politely and end the conversation
- If the user asks a follow-up question, try to provide additional context or clarification
- Speak Tagalog or Tagalog-English mix if the user does so

Context about the company:
{context}

Question: {request.question}

Answer:"""
        
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.1
        )
        
        answer = response.choices[0].message.content
        
        # Store conversation history
        conversation_data = {
            "question": request.question,
            "answer": answer,
            "sources": json.dumps(list(set(sources))),
            "timestamp": datetime.now().isoformat(),
            "user_id": request.user_id
        }
        
        redis_client.hset(f"conversation:{conversation_id}", mapping=conversation_data)
        redis_client.expire(f"conversation:{conversation_id}", 604800)  # 7 days
        
        return QueryResponse(
            answer=answer,
            sources=list(set(sources)),
            conversation_id=conversation_id,
            timestamp=conversation_data["timestamp"]
        )
        
    except Exception as e:
        logger.error(f"Error generating answer: {e}")
        raise HTTPException(status_code=500, detail="Error generating answer")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
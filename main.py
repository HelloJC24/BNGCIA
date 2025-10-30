"""
FastAPI RAG API Server
Provides endpoints for building and querying the RAG system with conversation history
"""
import os
import json
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging

import redis
import numpy as np
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Import our local RAG functions
from rag_website import (
    build_corpus_from_urls,
    embed_texts,
    cosine_sim,
    answer_with_context,
    load_local_corpus,
    DEFAULT_URLS,
    client as openai_client,
    LLM_MODEL,
    TOP_K
)

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Company RAG API",
    description="RAG system for company websites with conversation history",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Redis connection
REDIS_URL = os.getenv("REDIS_URL", "redis://default:987654321@72.60.43.106:6379")
try:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    redis_client.ping()
    logger.info("Connected to Redis successfully")
except Exception as e:
    logger.warning(f"Redis connection failed: {e}. Conversation history will be disabled.")
    redis_client = None

# Constants
CORPUS_REDIS_KEY = "rag:corpus"
CONVERSATION_PREFIX = "rag:conversation:"
CONVERSATION_EXPIRY = timedelta(days=7)  # Conversations expire after 7 days

# Pydantic models
class BuildRequest(BaseModel):
    urls: Optional[List[str]] = None
    force_rebuild: bool = False

class QueryRequest(BaseModel):
    query: str
    user_id: str  # Changed from EmailStr to str to avoid dependency issues
    max_context_chars: Optional[int] = 4000
    top_k: Optional[int] = 5

class QueryResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]
    conversation_id: str
    timestamp: datetime

class ConversationMessage(BaseModel):
    role: str  # "user" or "assistant" 
    content: str
    timestamp: datetime
    sources: Optional[List[Dict[str, Any]]] = None

class BuildResponse(BaseModel):
    message: str
    documents_count: int
    urls_processed: int
    timestamp: datetime

# Helper functions
def get_conversation_key(user_id: str) -> str:
    """Generate Redis key for user conversation"""
    user_hash = hashlib.md5(user_id.encode()).hexdigest()
    return f"{CONVERSATION_PREFIX}{user_hash}"

def save_corpus_to_redis(corpus: List[Dict[str, Any]]) -> bool:
    """Save corpus to Redis"""
    if not redis_client:
        logger.error("Redis client not available")
        return False
    
    try:
        # Clear existing corpus
        existing_doc_ids = redis_client.smembers(CORPUS_REDIS_KEY)
        if existing_doc_ids:
            logger.info(f"Clearing {len(existing_doc_ids)} existing documents from Redis")
            # Delete all existing document keys
            for doc_id in existing_doc_ids:
                redis_client.delete(f"{CORPUS_REDIS_KEY}:{doc_id}")
            # Clear the corpus set
            redis_client.delete(CORPUS_REDIS_KEY)
        
        # Save each document with progress logging
        saved_count = 0
        for doc in corpus:
            doc_key = f"{CORPUS_REDIS_KEY}:{doc['id']}"
            # Convert numpy array to list for JSON serialization
            doc_data = {
                "id": doc["id"],
                "url": doc["url"],
                "text": doc["text"],
                "embedding": doc["embedding"].tolist() if isinstance(doc["embedding"], np.ndarray) else doc["embedding"]
            }
            
            # Save document data
            redis_client.hset(doc_key, mapping={
                "data": json.dumps(doc_data)
            })
            
            # Add to corpus set
            redis_client.sadd(CORPUS_REDIS_KEY, doc["id"])
            saved_count += 1
            
            # Log progress every 50 documents
            if saved_count % 50 == 0:
                logger.info(f"Saved {saved_count}/{len(corpus)} documents to Redis...")
        
        logger.info(f"Successfully saved {saved_count} documents to Redis")
        
        # Verify the save by checking count
        redis_count = redis_client.scard(CORPUS_REDIS_KEY)
        if redis_count != len(corpus):
            logger.warning(f"Redis count ({redis_count}) doesn't match corpus size ({len(corpus)})")
        
        return True
    except Exception as e:
        logger.error(f"Error saving corpus to Redis: {e}")
        return False

def load_corpus_from_redis() -> List[Dict[str, Any]]:
    """Load corpus from Redis"""
    if not redis_client:
        logger.warning("Redis client not available")
        return []
    
    try:
        # Get all document IDs
        doc_ids = redis_client.smembers(CORPUS_REDIS_KEY)
        if not doc_ids:
            logger.info("No documents found in Redis corpus")
            return []
        
        logger.info(f"Loading {len(doc_ids)} documents from Redis...")
        
        corpus = []
        loaded_count = 0
        
        for doc_id in doc_ids:
            doc_key = f"{CORPUS_REDIS_KEY}:{doc_id}"
            doc_data_str = redis_client.hget(doc_key, "data")
            if doc_data_str:
                try:
                    doc_data = json.loads(doc_data_str)
                    # Convert embedding back to numpy array
                    doc_data["embedding"] = np.array(doc_data["embedding"], dtype=np.float32)
                    corpus.append(doc_data)
                    loaded_count += 1
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse document {doc_id}: {e}")
                    continue
            else:
                logger.warning(f"No data found for document {doc_id}")
        
        logger.info(f"Successfully loaded {loaded_count} documents from Redis")
        return corpus
    except Exception as e:
        logger.error(f"Error loading corpus from Redis: {e}")
        return []

def save_conversation_message(user_id: str, message: ConversationMessage) -> bool:
    """Save conversation message to Redis"""
    if not redis_client:
        return False
    
    try:
        conv_key = get_conversation_key(user_id)
        message_data = message.model_dump_json()
        
        # Add message to conversation list
        redis_client.lpush(conv_key, message_data)
        
        # Set expiration
        redis_client.expire(conv_key, CONVERSATION_EXPIRY)
        
        # Keep only last 50 messages per user
        redis_client.ltrim(conv_key, 0, 49)
        
        return True
    except Exception as e:
        logger.error(f"Error saving conversation message: {e}")
        return False

def get_conversation_history(user_id: str, limit: int = 10) -> List[ConversationMessage]:
    """Get conversation history for user"""
    if not redis_client:
        return []
    
    try:
        conv_key = get_conversation_key(user_id)
        messages_data = redis_client.lrange(conv_key, 0, limit - 1)
        
        messages = []
        for msg_data in reversed(messages_data):  # Reverse to get chronological order
            try:
                message = ConversationMessage.model_validate_json(msg_data)
                messages.append(message)
            except Exception as e:
                logger.warning(f"Error parsing conversation message: {e}")
                continue
        
        return messages
    except Exception as e:
        logger.error(f"Error getting conversation history: {e}")
        return []

def retrieve_with_context_and_history(
    query: str, 
    corpus: List[Dict[str, Any]], 
    user_id: str,
    top_k: int = TOP_K,
    max_context_chars: int = 4000
) -> Dict[str, Any]:
    """Enhanced retrieval that considers conversation history"""
    
    # Get conversation history
    history = get_conversation_history(user_id, limit=5)
    
    # Build context-aware query
    context_query = query
    if history:
        recent_context = " ".join([msg.content for msg in history[-3:] if msg.role == "user"])
        context_query = f"Previous context: {recent_context}\n\nCurrent question: {query}"
    
    # Embed the enhanced query
    try:
        q_emb = embed_texts([context_query])[0]
    except Exception as e:
        logger.error(f"Error embedding query: {e}")
        # Fallback to original query
        q_emb = embed_texts([query])[0]
    
    # Calculate similarities
    similarities = []
    for doc in corpus:
        try:
            similarity = cosine_sim(q_emb, doc["embedding"])
            similarities.append((similarity, doc))
        except Exception as e:
            logger.warning(f"Error calculating similarity: {e}")
            continue
    
    # Sort and filter
    similarities.sort(key=lambda x: x[0], reverse=True)
    top_docs = similarities[:top_k]
    
    # Build context
    context_pieces = []
    total_chars = 0
    sources = []
    
    for score, doc in top_docs:
        if score < 0.3:  # Minimum relevance threshold
            break
            
        snippet = doc["text"]
        source_info = f"[Source: {doc['url']} (relevance: {score:.2f})]\n{snippet}\n"
        
        if total_chars + len(source_info) > max_context_chars:
            break
        
        context_pieces.append(source_info)
        total_chars += len(source_info)
        
        sources.append({
            "score": float(score),
            "id": doc["id"],
            "url": doc["url"],
            "text": snippet[:200] + "..." if len(snippet) > 200 else snippet
        })
    
    context = "\n---\n".join(context_pieces)
    
    # Build conversation-aware prompt
    system_prompt = (
        "You are a knowledgeable assistant for company information. "
        "Answer questions using ONLY the provided sources. "
        "If information isn't in the sources, say you don't have that information. "
        "Be conversational and reference previous context when relevant. "
        "Always cite sources with URLs."
    )
    
    # Include conversation history in prompt
    conversation_context = ""
    if history:
        conversation_context = "\nPREVIOUS CONVERSATION:\n"
        for msg in history[-3:]:  # Last 3 messages for context
            conversation_context += f"{msg.role.upper()}: {msg.content}\n"
    
    user_prompt = f"""
{conversation_context}

CURRENT QUESTION: {query}

SOURCES:
{context}

Please answer the current question using the provided sources and considering the conversation context.
"""
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    
    try:
        resp = openai_client.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
            temperature=0.1,
            max_tokens=1000
        )
        answer = resp.choices[0].message.content
        logger.info("Generated answer successfully")
    except Exception as e:
        logger.error(f"Error generating answer: {e}")
        answer = "I encountered an error while generating the answer. Please try again."
    
    return {
        "answer": answer,
        "sources": sources
    }

# API Endpoints
@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "Company RAG API is running",
        "redis_connected": redis_client is not None,
        "timestamp": datetime.now()
    }

@app.post("/prep-rag", response_model=BuildResponse)
async def build_rag(request: BuildRequest, background_tasks: BackgroundTasks):
    """Build or rebuild the RAG corpus"""
    try:
        urls = request.urls or DEFAULT_URLS
        
        logger.info(f"Building RAG corpus from {len(urls)} URLs")
        
        # Check if corpus exists in Redis and force_rebuild is False
        if not request.force_rebuild and redis_client:
            existing_corpus = load_corpus_from_redis()
            if existing_corpus:
                return BuildResponse(
                    message="Corpus already exists. Use force_rebuild=true to rebuild.",
                    documents_count=len(existing_corpus),
                    urls_processed=len(set(doc["url"] for doc in existing_corpus)),
                    timestamp=datetime.now()
                )
        
        # Build corpus
        corpus = build_corpus_from_urls(urls, out_json="corpus_api.json")
        
        if not corpus:
            raise HTTPException(status_code=500, detail="Failed to build corpus")
        
        # Save to Redis immediately (not in background)
        if redis_client:
            success = save_corpus_to_redis(corpus)
            if not success:
                logger.warning("Failed to save corpus to Redis, but continuing...")
        else:
            raise HTTPException(status_code=500, detail="Redis not available. Cannot save corpus.")
        
        return BuildResponse(
            message="RAG corpus built successfully",
            documents_count=len(corpus),
            urls_processed=len(set(doc["url"] for doc in corpus)),
            timestamp=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Error building RAG corpus: {e}")
        raise HTTPException(status_code=500, detail=f"Error building corpus: {str(e)}")

@app.post("/ask", response_model=QueryResponse)
async def ask_question(request: QueryRequest):
    """Ask a question to the RAG system"""
    try:
        # Load corpus from Redis only (no fallback to local files)
        corpus = load_corpus_from_redis()
        
        if not corpus:
            raise HTTPException(
                status_code=404, 
                detail="No corpus found in Redis. Please build the corpus first using /prep-rag endpoint"
            )
        
        # Save user question to conversation history
        user_message = ConversationMessage(
            role="user",
            content=request.query,
            timestamp=datetime.now()
        )
        save_conversation_message(request.user_id, user_message)
        
        # Get answer with conversation context
        result = retrieve_with_context_and_history(
            query=request.query,
            corpus=corpus,
            user_id=request.user_id,
            top_k=request.top_k,
            max_context_chars=request.max_context_chars
        )
        
        # Save assistant response to conversation history
        assistant_message = ConversationMessage(
            role="assistant",
            content=result["answer"],
            timestamp=datetime.now(),
            sources=result["sources"]
        )
        save_conversation_message(request.user_id, assistant_message)
        
        # Generate conversation ID
        conversation_id = hashlib.md5(f"{request.user_id}:{datetime.now().isoformat()}".encode()).hexdigest()
        
        return QueryResponse(
            answer=result["answer"],
            sources=result["sources"],
            conversation_id=conversation_id,
            timestamp=datetime.now()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")

@app.get("/conversation/{user_id}")
async def get_conversation(user_id: str, limit: int = 20):
    """Get conversation history for a user"""
    try:
        history = get_conversation_history(user_id, limit=limit)
        return {
            "user_id": user_id,
            "messages": history,
            "count": len(history),
            "timestamp": datetime.now()
        }
    except Exception as e:
        logger.error(f"Error getting conversation history: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting conversation: {str(e)}")

@app.delete("/conversation/{user_id}")
async def clear_conversation(user_id: str):
    """Clear conversation history for a user"""
    try:
        if redis_client:
            conv_key = get_conversation_key(user_id)
            redis_client.delete(conv_key)
            return {"message": f"Conversation history cleared for {user_id}"}
        else:
            return {"message": "Redis not available, no conversation history to clear"}
    except Exception as e:
        logger.error(f"Error clearing conversation: {e}")
        raise HTTPException(status_code=500, detail=f"Error clearing conversation: {str(e)}")

@app.post("/migrate-corpus")
async def migrate_local_corpus_to_redis():
    """Migrate existing local corpus to Redis"""
    try:
        if not redis_client:
            raise HTTPException(status_code=500, detail="Redis not available")
        
        # Try to load from local files
        corpus = load_local_corpus("corpus_local.json")
        if not corpus:
            corpus = load_local_corpus("corpus_api.json")
        
        if not corpus:
            raise HTTPException(status_code=404, detail="No local corpus found to migrate")
        
        # Save to Redis
        success = save_corpus_to_redis(corpus)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save corpus to Redis")
        
        return {
            "message": "Local corpus migrated to Redis successfully",
            "documents_migrated": len(corpus),
            "timestamp": datetime.now()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error migrating corpus: {e}")
        raise HTTPException(status_code=500, detail=f"Error migrating corpus: {str(e)}")

@app.get("/corpus/stats")
async def get_corpus_stats():
    """Get corpus statistics"""
    try:
        # Load corpus from Redis only
        corpus = load_corpus_from_redis()
        
        if not corpus:
            return {
                "message": "No corpus found in Redis",
                "total_documents": 0,
                "unique_urls": 0,
                "total_characters": 0,
                "average_chunk_size": 0,
                "urls": [],
                "timestamp": datetime.now()
            }
        
        urls = set()
        total_chars = 0
        
        for doc in corpus:
            urls.add(doc["url"])
            total_chars += len(doc["text"])
        
        return {
            "total_documents": len(corpus),
            "unique_urls": len(urls),
            "total_characters": total_chars,
            "average_chunk_size": total_chars // len(corpus) if corpus else 0,
            "urls": sorted(list(urls)),
            "timestamp": datetime.now()
        }
        
    except Exception as e:
        logger.error(f"Error getting corpus stats: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting stats: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
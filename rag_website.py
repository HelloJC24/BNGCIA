"""
rag_website.py
- Crawl given domains locally
- Chunk & embed text via OpenAI
- Perform local vector search using cosine similarity
- Fully local RAG implementation without external dependencies
"""
import os
import re
import json
import time
import hashlib
import logging
from urllib.parse import urljoin, urlparse
from collections import deque
from typing import List, Dict, Any, Tuple

import requests
from bs4 import BeautifulSoup
import numpy as np
from tqdm import tqdm
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

from openai import OpenAI

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# load .env
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI")
if not OPENAI_API_KEY:
    raise ValueError("Please set OPENAI_API_KEY in your .env file")
client = OpenAI(api_key=OPENAI_API_KEY)

# ---------- CONFIG ----------
DEFAULT_URLS = [
    "https://thebngc.com",
    "https://gogel.thebngc.com",
    "https://gogel.thebngc.com/agents",
    "https://uptura-tech.com"
]
CHUNK_SIZE = 800  # Increased for better context
CHUNK_OVERLAP = 150  # Increased overlap for better continuity
EMBED_MODEL = "text-embedding-3-small"
LLM_MODEL = "gpt-4o-mini"  # Better model for more accurate responses
TOP_K = 5  # Increased to get more context
CRAWL_MAX_PAGES = 300  # Increased for more comprehensive crawling
REQUEST_TIMEOUT = 15  # Increased timeout
USER_AGENT = "RAGCrawler/2.0 (+https://thebngc.com)"
SIMILARITY_THRESHOLD = 0.3  # Lower threshold for better recall
# ---------------------------

session = requests.Session()
session.headers.update({"User-Agent": USER_AGENT})

# ---------- UTIL ----------
def text_from_html(html: str) -> str:
    """Extract clean text from HTML content."""
    soup = BeautifulSoup(html, "html.parser")
    
    # Remove unwanted elements
    for s in soup(["script", "style", "noscript", "iframe", "nav", "footer", "header", "aside"]):
        s.decompose()
    
    texts = []
    # Prioritize important content
    for tag in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "article", "section", "div"]):
        t = tag.get_text(separator=" ", strip=True)
        if t and len(t.strip()) > 10:  # Filter out very short text
            texts.append(t)
    
    return "\n".join(texts).strip()

def fetch_rendered_html(url: str) -> str:
    """Fetch HTML content using Playwright for JavaScript-heavy pages."""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="networkidle", timeout=30000)
            html = page.content()
            browser.close()
            logger.info(f"Successfully fetched rendered HTML for {url}")
            return html
    except Exception as e:
        logger.warning(f"Failed to fetch rendered HTML for {url}: {e}")
        return ""

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Split text into overlapping chunks."""
    if not text:
        return []
    
    # Clean up whitespace
    text = re.sub(r"\s+", " ", text).strip()
    
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    text_length = len(text)
    
    while start < text_length:
        end = start + chunk_size
        
        # Try to break at sentence boundaries
        if end < text_length:
            # Look for sentence endings within the last 100 characters
            last_period = text.rfind('.', start, end)
            last_exclamation = text.rfind('!', start, end)
            last_question = text.rfind('?', start, end)
            
            best_break = max(last_period, last_exclamation, last_question)
            if best_break > start + chunk_size // 2:  # Only if it's not too early
                end = best_break + 1
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        start = end - overlap
        if start < 0:
            break
    
    return chunks

def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    """Calculate cosine similarity between two vectors."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
    
    return float(np.dot(a, b) / (norm_a * norm_b))

def id_for(url: str, text: str) -> str:
    """Generate unique ID for a document chunk."""
    key = f"{url}||{text[:200]}"  # Use more text for uniqueness
    return hashlib.sha256(key.encode()).hexdigest()

# ---------- IMPROVED CRAWLER ----------
def crawl(start_urls: List[str], same_host_only: bool = True, max_pages: int = CRAWL_MAX_PAGES) -> Dict[str, str]:
    """Crawl websites and extract text content."""
    parsed_hosts = {urlparse(u).netloc for u in start_urls}
    visited = set()
    q = deque(start_urls)
    results = {}
    
    logger.info(f"Starting crawl of {len(start_urls)} URLs, max pages: {max_pages}")
    
    while q and len(visited) < max_pages:
        url = q.popleft()
        if url in visited:
            continue
        
        visited.add(url)
        logger.info(f"Crawling ({len(visited)}/{max_pages}): {url}")
        
        try:
            # First try regular requests
            resp = session.get(url, timeout=REQUEST_TIMEOUT)
            if resp.status_code != 200:
                logger.warning(f"HTTP {resp.status_code} for {url}")
                continue
            
            # Use Playwright for JavaScript-heavy pages
            html = fetch_rendered_html(url)
            if not html:
                # Fallback to regular HTML if Playwright fails
                html = resp.text
            
            text = text_from_html(html)
            if text and len(text.strip()) > 100:  # Only store substantial content
                results[url] = text
                logger.info(f"Extracted {len(text)} characters from {url}")
            
            # Find new links
            soup = BeautifulSoup(resp.text, "html.parser")
            for a in soup.find_all("a", href=True):
                href = urljoin(url, a["href"])
                parsed = urlparse(href)
                
                # Skip non-HTTP URLs
                if parsed.scheme not in ("http", "https"):
                    continue
                
                # Check host restriction
                if same_host_only and parsed.netloc not in parsed_hosts:
                    continue
                
                # Clean URL (remove fragments and query params)
                href_clean = parsed._replace(fragment="", query="").geturl()
                
                # Skip certain file types
                if any(href_clean.lower().endswith(ext) for ext in ['.pdf', '.jpg', '.png', '.gif', '.css', '.js']):
                    continue
                
                if href_clean not in visited and href_clean not in q:
                    q.append(href_clean)
        
        except Exception as e:
            logger.error(f"Error crawling {url}: {e}")
            continue
    
    logger.info(f"Crawling complete. Found {len(results)} pages with content.")
    return results

# ---------- IMPROVED EMBEDDINGS ----------
def embed_texts(texts: List[str]) -> List[np.ndarray]:
    """Embed a list of texts using OpenAI's embedding model."""
    if not texts:
        return []
    
    EMBED_BATCH = 100  # Increased batch size for efficiency
    vectors = []
    
    logger.info(f"Embedding {len(texts)} text chunks...")
    
    for i in tqdm(range(0, len(texts), EMBED_BATCH), desc="Embedding batches"):
        batch = texts[i:i+EMBED_BATCH]
        try:
            resp = client.embeddings.create(
                model=EMBED_MODEL,
                input=batch
            )
            batch_vectors = [np.array(item.embedding, dtype=np.float32) for item in resp.data]
            vectors.extend(batch_vectors)
        except Exception as e:
            logger.error(f"Error embedding batch {i//EMBED_BATCH + 1}: {e}")
            # Add zero vectors as fallback
            vectors.extend([np.zeros(1536, dtype=np.float32) for _ in batch])
    
    logger.info(f"Successfully embedded {len(vectors)} chunks")
    return vectors

def build_corpus_from_urls(urls: List[str], out_json: str = "corpus_local.json") -> List[Dict[str, Any]]:
    """Build a corpus by crawling URLs and creating embeddings."""
    logger.info(f"Building corpus from URLs: {urls}")
    
    # Crawl websites
    pages = crawl(urls, same_host_only=True, max_pages=CRAWL_MAX_PAGES)
    logger.info(f"Found {len(pages)} pages with content")
    
    if not pages:
        logger.warning("No pages found during crawling")
        return []
    
    # Process text into chunks
    all_chunks = []
    provenance = []
    
    for url, text in pages.items():
        chunks = chunk_text(text)
        logger.info(f"Created {len(chunks)} chunks from {url}")
        
        for chunk in chunks:
            if len(chunk.strip()) < 50:  # Skip very short chunks
                continue
            
            uid = id_for(url, chunk)
            all_chunks.append(chunk)
            provenance.append({"id": uid, "url": url, "text": chunk})
    
    logger.info(f"Total chunks to embed: {len(all_chunks)}")
    
    if not all_chunks:
        logger.warning("No chunks found after processing")
        return []
    
    # Create embeddings
    embeddings = embed_texts(all_chunks)
    
    # Build corpus
    corpus = []
    for meta, emb in zip(provenance, embeddings):
        doc = {
            "id": meta["id"],
            "url": meta["url"],
            "text": meta["text"],
            "embedding": emb.tolist()  # Convert to list for JSON serialization
        }
        corpus.append(doc)
    
    # Save to file
    try:
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(corpus, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved corpus with {len(corpus)} documents to {out_json}")
    except Exception as e:
        logger.error(f"Error saving corpus: {e}")
    
    return corpus

def load_local_corpus(path: str = "corpus_local.json") -> List[Dict[str, Any]]:
    """Load corpus from local JSON file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            corpus = json.load(f)
        
        # Convert embeddings back to numpy arrays
        for doc in corpus:
            doc["embedding"] = np.array(doc["embedding"], dtype=np.float32)
        
        logger.info(f"Loaded corpus with {len(corpus)} documents from {path}")
        return corpus
    
    except FileNotFoundError:
        logger.error(f"Corpus file {path} not found")
        return []
    except Exception as e:
        logger.error(f"Error loading corpus: {e}")
        return []

# ---------- IMPROVED RETRIEVAL ----------
def retrieve_knn(question: str, corpus: List[Dict[str, Any]], top_k: int = TOP_K) -> List[Dict[str, Any]]:
    """Retrieve most similar documents using cosine similarity."""
    if not corpus:
        logger.warning("Empty corpus provided for retrieval")
        return []
    
    # Embed the question
    try:
        q_emb = embed_texts([question])[0]
    except Exception as e:
        logger.error(f"Error embedding question: {e}")
        return []
    
    # Calculate similarities
    similarities = []
    for doc in corpus:
        try:
            similarity = cosine_sim(q_emb, doc["embedding"])
            similarities.append((similarity, doc))
        except Exception as e:
            logger.warning(f"Error calculating similarity for doc {doc.get('id', 'unknown')}: {e}")
            continue
    
    # Sort by similarity (descending)
    similarities.sort(key=lambda x: x[0], reverse=True)
    
    # Filter by threshold and return top-k
    filtered_results = []
    for score, doc in similarities[:top_k]:
        if score >= SIMILARITY_THRESHOLD:
            filtered_results.append({
                "score": float(score),
                "id": doc["id"],
                "url": doc["url"],
                "text": doc["text"]
            })
    
    logger.info(f"Retrieved {len(filtered_results)} relevant documents (threshold: {SIMILARITY_THRESHOLD})")
    return filtered_results

def answer_with_context(question: str, corpus: List[Dict[str, Any]], top_k: int = TOP_K, max_context_chars: int = 4000) -> Dict[str, Any]:
    """Generate an answer using retrieved context."""
    retrieved = retrieve_knn(question, corpus, top_k=top_k)
    
    if not retrieved:
        return {
            "answer": "I don't have enough relevant information in my knowledge base to answer this question.",
            "retrieved": []
        }
    
    # Build context from retrieved documents
    context_pieces = []
    total_chars = 0
    
    for i, doc in enumerate(retrieved, 1):
        snippet = doc["text"]
        source_info = f"[Source {i}: {doc['url']} (relevance: {doc['score']:.2f})]\n{snippet}\n"
        
        if total_chars + len(source_info) > max_context_chars:
            break
        
        context_pieces.append(source_info)
        total_chars += len(source_info)
    
    context = "\n---\n".join(context_pieces)
    
    # Create prompts
    system_prompt = (
        "You are a knowledgeable assistant that answers questions using ONLY the provided source materials. "
        "If the answer is not contained in the sources, clearly state that you don't have that information. "
        "Always cite the specific sources you used in your answer with their URLs. "
        "Be accurate, helpful, and concise."
    )
    
    user_prompt = f"""
QUESTION: {question}

SOURCES:
{context}

Please answer the question based on the provided sources. Include citations with URLs for any information you use.
"""
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    
    try:
        resp = client.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
            temperature=0.1,  # Lower temperature for more consistent answers
            max_tokens=1000
        )
        answer = resp.choices[0].message.content
        logger.info("Generated answer successfully")
    except Exception as e:
        logger.error(f"Error generating answer: {e}")
        answer = "I encountered an error while generating the answer. Please try again."
    
    return {
        "answer": answer,
        "retrieved": retrieved
    }

# ---------- INTERACTIVE FUNCTIONS ----------
def search_corpus(corpus: List[Dict[str, Any]], query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """Search corpus for documents containing specific terms."""
    results = []
    query_lower = query.lower()
    
    for doc in corpus:
        if query_lower in doc["text"].lower():
            results.append({
                "url": doc["url"],
                "text": doc["text"][:200] + "..." if len(doc["text"]) > 200 else doc["text"],
                "full_text": doc["text"]
            })
            
            if len(results) >= max_results:
                break
    
    return results

def get_corpus_stats(corpus: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Get statistics about the corpus."""
    if not corpus:
        return {"total_docs": 0}
    
    urls = set()
    total_chars = 0
    
    for doc in corpus:
        urls.add(doc["url"])
        total_chars += len(doc["text"])
    
    return {
        "total_docs": len(corpus),
        "unique_urls": len(urls),
        "avg_chunk_size": total_chars // len(corpus) if corpus else 0,
        "total_characters": total_chars,
        "urls": sorted(list(urls))
    }

# ---------- CLI ----------
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Local RAG system for company websites")
    parser.add_argument("--urls", nargs="+", default=DEFAULT_URLS, help="start urls to crawl")
    parser.add_argument("--out", default="corpus_local.json", help="local json output file")
    parser.add_argument("--build", action="store_true", help="crawl, embed and save corpus")
    parser.add_argument("--query", help="ask a question using local corpus")
    parser.add_argument("--search", help="search corpus for specific terms")
    parser.add_argument("--stats", action="store_true", help="show corpus statistics")
    parser.add_argument("--interactive", action="store_true", help="start interactive mode")
    args = parser.parse_args()

    if args.build:
        logger.info("Building corpus from URLs...")
        corpus = build_corpus_from_urls(args.urls, out_json=args.out)
        if corpus:
            logger.info(f"Successfully built corpus with {len(corpus)} chunks")
        else:
            logger.error("Failed to build corpus")
    
    if args.stats:
        corpus = load_local_corpus(args.out)
        stats = get_corpus_stats(corpus)
        print("\n--- CORPUS STATISTICS ---")
        print(f"Total documents: {stats['total_docs']}")
        print(f"Unique URLs: {stats['unique_urls']}")
        print(f"Average chunk size: {stats['avg_chunk_size']} characters")
        print(f"Total characters: {stats['total_characters']}")
        print("\nURLs in corpus:")
        for url in stats.get('urls', []):
            print(f"  - {url}")
    
    if args.search:
        corpus = load_local_corpus(args.out)
        results = search_corpus(corpus, args.search)
        print(f"\n--- SEARCH RESULTS for '{args.search}' ---")
        for i, result in enumerate(results, 1):
            print(f"\n{i}. {result['url']}")
            print(f"   {result['text']}")
    
    if args.query:
        corpus = load_local_corpus(args.out)
        if not corpus:
            logger.error("No corpus found. Run with --build first.")
        else:
            result = answer_with_context(args.query, corpus)
            print("\n--- ANSWER ---")
            print(result["answer"])
            print("\n--- SOURCES ---")
            for i, source in enumerate(result["retrieved"], 1):
                print(f"{i}. [{source['score']:.3f}] {source['url']}")
    
    if args.interactive:
        corpus = load_local_corpus(args.out)
        if not corpus:
            logger.error("No corpus found. Run with --build first.")
        else:
            print("\n=== Interactive RAG System ===")
            print("Type 'quit' to exit, 'stats' for corpus info, or ask a question.")
            
            while True:
                try:
                    question = input("\nQuestion: ").strip()
                    if question.lower() in ['quit', 'exit', 'q']:
                        break
                    elif question.lower() == 'stats':
                        stats = get_corpus_stats(corpus)
                        print(f"Corpus has {stats['total_docs']} documents from {stats['unique_urls']} URLs")
                    elif question:
                        result = answer_with_context(question, corpus)
                        print(f"\nAnswer: {result['answer']}")
                        if result['retrieved']:
                            print(f"\nBased on {len(result['retrieved'])} sources:")
                            for source in result['retrieved']:
                                print(f"  - {source['url']} (relevance: {source['score']:.2f})")
                except KeyboardInterrupt:
                    print("\nGoodbye!")
                    break
                except Exception as e:
                    print(f"Error: {e}")

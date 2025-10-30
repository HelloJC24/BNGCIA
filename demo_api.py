"""
Simple demo script to show the API functionality
This will demonstrate the API endpoints using the corpus we already have
"""
import json
from datetime import datetime
from main import app, load_local_corpus, answer_with_context, get_corpus_stats

def demo_api_functionality():
    """Demonstrate the core API functionality"""
    print("🚀 RAG API Functionality Demo")
    print("=" * 50)
    
    # Load existing corpus
    print("📂 Loading existing corpus...")
    corpus = load_local_corpus("corpus_local.json")
    
    if not corpus:
        print("❌ No corpus found. Please run the local RAG system first to build a corpus.")
        return
    
    print(f"✅ Loaded corpus with {len(corpus)} documents")
    
    # Simulate corpus statistics endpoint
    print("\n📊 Corpus Statistics:")
    urls = set()
    total_chars = 0
    
    for doc in corpus:
        urls.add(doc["url"])
        total_chars += len(doc["text"])
    
    stats = {
        "total_documents": len(corpus),
        "unique_urls": len(urls),
        "total_characters": total_chars,
        "average_chunk_size": total_chars // len(corpus) if corpus else 0,
        "urls": sorted(list(urls))
    }
    
    print(f"   • Total documents: {stats['total_documents']}")
    print(f"   • Unique URLs: {stats['unique_urls']}")
    print(f"   • Total characters: {stats['total_characters']}")
    print(f"   • Average chunk size: {stats['average_chunk_size']}")
    print(f"   • Websites covered: {len(stats['urls'])}")
    
    # Simulate /ask endpoint
    print("\n❓ Testing Question-Answer Functionality:")
    test_queries = [
        {
            "query": "What is GoGel Real Estate?",
            "user_id": "demo@example.com"
        },
        {
            "query": "Tell me about Atty. Philip Ray L. Nangkil",
            "user_id": "demo@example.com"
        },
        {
            "query": "What services does Uptura Tech provide?",
            "user_id": "user2@example.com"
        }
    ]
    
    for i, test_query in enumerate(test_queries, 1):
        print(f"\n{i}. Query: {test_query['query']}")
        print(f"   User: {test_query['user_id']}")
        
        try:
            # This simulates the /ask endpoint logic
            result = answer_with_context(test_query['query'], corpus)
            
            # Format response like the API would
            api_response = {
                "answer": result["answer"],
                "sources": [
                    {
                        "score": source["score"],
                        "id": source["id"],
                        "url": source["url"],
                        "text": source["text"][:200] + "..." if len(source["text"]) > 200 else source["text"]
                    }
                    for source in result["retrieved"]
                ],
                "conversation_id": f"demo_{i}_{datetime.now().strftime('%H%M%S')}",
                "timestamp": datetime.now().isoformat()
            }
            
            print(f"   Answer: {api_response['answer'][:150]}...")
            print(f"   Sources: {len(api_response['sources'])} documents found")
            print(f"   Conversation ID: {api_response['conversation_id']}")
            
            if api_response['sources']:
                best_source = api_response['sources'][0]
                print(f"   Best match: {best_source['url']} (score: {best_source['score']:.3f})")
        
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    # Show what the API endpoints would look like
    print("\n🔗 API Endpoints Available:")
    print("   POST /prep-rag     - Build/rebuild corpus")
    print("   POST /ask          - Ask questions with conversation history")
    print("   GET  /conversation/{user_id} - Get conversation history")
    print("   DELETE /conversation/{user_id} - Clear conversation")
    print("   GET  /corpus/stats - Get corpus statistics")
    print("   GET  /             - Health check")
    
    print("\n📋 Example API Usage:")
    example_request = {
        "query": "What services does GoGel provide?",
        "user_id": "user@example.com",
        "max_context_chars": 4000,
        "top_k": 5
    }
    
    print("   curl -X POST http://localhost:8000/ask \\")
    print("        -H 'Content-Type: application/json' \\")
    print(f"        -d '{json.dumps(example_request, indent=8)}'")
    
    print("\n✅ Demo completed!")
    print("\nTo start the actual API server:")
    print("   1. Install Redis: docker run -d -p 6379:6379 redis:7-alpine")
    print("   2. Start API: python main.py")
    print("   3. Visit docs: http://localhost:8000/docs")

if __name__ == "__main__":
    demo_api_functionality()
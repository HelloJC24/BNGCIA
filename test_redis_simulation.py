"""
Test the Redis-based API functionality with a simple local simulation
"""
from main import (
    retrieve_with_context_and_history,
    load_corpus_from_redis,
    QueryRequest
)

def simulate_api_ask_endpoint():
    """Simulate the /ask endpoint using Redis-stored corpus"""
    print("🤖 Simulating Redis-based API /ask Endpoint")
    print("=" * 45)
    
    # Load corpus from Redis (same as API does)
    print("📂 Loading corpus from Redis...")
    corpus = load_corpus_from_redis()
    
    if not corpus:
        print("❌ No corpus found in Redis")
        return
    
    print(f"✅ Loaded {len(corpus)} documents from Redis")
    
    # Simulate API requests
    test_queries = [
        {
            "query": "What is GoGel Real Estate?",
            "user_id": "api_test@redis.com",
            "max_context_chars": 4000,
            "top_k": 5
        },
        {
            "query": "Tell me about Atty. Philip Ray L. Nangkil",
            "user_id": "api_test@redis.com",
            "max_context_chars": 4000,
            "top_k": 5
        },
        {
            "query": "What services does Uptura Tech provide?",
            "user_id": "tech_user@redis.com",
            "max_context_chars": 4000,
            "top_k": 5
        }
    ]
    
    for i, query_data in enumerate(test_queries, 1):
        print(f"\n🔍 Query {i}: {query_data['query']}")
        print(f"   User: {query_data['user_id']}")
        
        try:
            # This is exactly what the /ask endpoint does
            result = retrieve_with_context_and_history(
                query=query_data['query'],
                corpus=corpus,
                user_id=query_data['user_id'],
                top_k=query_data['top_k'],
                max_context_chars=query_data['max_context_chars']
            )
            
            print(f"   ✅ Answer: {result['answer'][:150]}...")
            print(f"   📊 Sources: {len(result['sources'])} documents found")
            
            if result['sources']:
                best_source = result['sources'][0]
                print(f"   🎯 Best match: {best_source['url']} (score: {best_source['score']:.3f})")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print(f"\n🎉 Redis-based API simulation completed!")
    print(f"\n📝 Summary:")
    print(f"   • Corpus is stored entirely in Redis")
    print(f"   • No dependency on local JSON files")
    print(f"   • API can answer questions using Redis data")
    print(f"   • Conversation history is also stored in Redis")
    
    print(f"\n🚀 To test with actual HTTP API:")
    print(f"   1. Start server: python main.py")
    print(f"   2. POST to /ask with query and user_id")
    print(f"   3. Corpus will be loaded from Redis automatically")

if __name__ == "__main__":
    simulate_api_ask_endpoint()
"""
Direct Redis functionality test - no HTTP calls needed
This demonstrates the Redis storage and retrieval directly
"""
import json
from main import (
    save_corpus_to_redis, 
    load_corpus_from_redis, 
    load_local_corpus,
    redis_client
)

def test_redis_corpus_operations():
    """Test Redis corpus operations directly"""
    print("🔧 Testing Redis Corpus Operations")
    print("=" * 40)
    
    # Check Redis connection
    if not redis_client:
        print("❌ Redis not connected")
        return
    
    print("✅ Redis connected successfully")
    
    # Load existing local corpus
    print("\n📂 Loading local corpus...")
    local_corpus = load_local_corpus("corpus_local.json")
    
    if not local_corpus:
        print("❌ No local corpus found")
        return
    
    print(f"✅ Loaded {len(local_corpus)} documents from local file")
    
    # Save to Redis
    print("\n💾 Saving corpus to Redis...")
    success = save_corpus_to_redis(local_corpus)
    
    if success:
        print("✅ Corpus saved to Redis successfully")
    else:
        print("❌ Failed to save corpus to Redis")
        return
    
    # Load from Redis
    print("\n🔄 Loading corpus from Redis...")
    redis_corpus = load_corpus_from_redis()
    
    if redis_corpus:
        print(f"✅ Loaded {len(redis_corpus)} documents from Redis")
        
        # Verify data integrity
        if len(redis_corpus) == len(local_corpus):
            print("✅ Document count matches")
        else:
            print(f"⚠️ Document count mismatch: local={len(local_corpus)}, redis={len(redis_corpus)}")
        
        # Check a sample document
        if redis_corpus:
            sample_doc = redis_corpus[0]
            print(f"\n📄 Sample document:")
            print(f"   ID: {sample_doc['id'][:16]}...")
            print(f"   URL: {sample_doc['url']}")
            print(f"   Text length: {len(sample_doc['text'])} chars")
            print(f"   Embedding shape: {sample_doc['embedding'].shape}")
        
    else:
        print("❌ Failed to load corpus from Redis")
        return
    
    # Test stats
    print(f"\n📊 Corpus Statistics:")
    urls = set()
    total_chars = 0
    
    for doc in redis_corpus:
        urls.add(doc["url"])
        total_chars += len(doc["text"])
    
    print(f"   Total documents: {len(redis_corpus)}")
    print(f"   Unique URLs: {len(urls)}")
    print(f"   Total characters: {total_chars}")
    print(f"   Average chunk size: {total_chars // len(redis_corpus) if redis_corpus else 0}")
    
    print(f"\n🌐 URLs in corpus:")
    for url in sorted(urls):
        print(f"   • {url}")
    
    print(f"\n🎉 Redis corpus operations test completed successfully!")
    print(f"\nThe corpus is now stored in Redis and ready for API queries!")
    print(f"You can now use the /ask endpoint without needing local JSON files.")

if __name__ == "__main__":
    test_redis_corpus_operations()
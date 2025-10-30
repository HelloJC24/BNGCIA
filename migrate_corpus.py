#!/usr/bin/env python3
"""
Migrate local corpus to Redis for the API
"""
import json
import redis
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def migrate_corpus_to_redis():
    """Migrate corpus_local.json to Redis"""
    
    # Connect to Redis
    redis_url = os.getenv("REDIS_URL", "redis://default:987654321@72.60.43.106:6379")
    try:
        redis_client = redis.from_url(redis_url, decode_responses=True)
        redis_client.ping()
        print(f"✅ Connected to Redis at {redis_url}")
    except Exception as e:
        print(f"❌ Failed to connect to Redis: {e}")
        return False
    
    # Load local corpus
    try:
        with open("corpus_local.json", "r", encoding="utf-8") as f:
            local_corpus = json.load(f)
        print(f"✅ Loaded local corpus with {len(local_corpus)} documents")
    except Exception as e:
        print(f"❌ Failed to load local corpus: {e}")
        return False
    
    # Clear existing corpus in Redis
    print("🗑️ Clearing existing Redis corpus...")
    doc_ids = redis_client.smembers("corpus:documents")
    for doc_id in doc_ids:
        redis_client.delete(f"corpus:doc:{doc_id}")
    redis_client.delete("corpus:documents")
    redis_client.delete("corpus:metadata")
    
    # Migrate documents to Redis
    print("📤 Migrating documents to Redis...")
    migrated_count = 0
    
    for doc in local_corpus:
        try:
            doc_id = doc.get("id", migrated_count)
            
            # Store document in Redis with safe field access
            redis_data = {
                "text": doc.get("text", ""),
                "embedding": json.dumps(doc.get("embedding", [])),
                "source": doc.get("source", "unknown"),
                "created_at": doc.get("created_at", datetime.now().isoformat())
            }
            
            # Skip empty documents
            if not redis_data["text"] or not redis_data["embedding"]:
                print(f"   Skipping empty document {doc_id}")
                continue
            
            redis_client.hset(f"corpus:doc:{doc_id}", mapping=redis_data)
            redis_client.sadd("corpus:documents", doc_id)
            migrated_count += 1
            
            if migrated_count % 100 == 0:
                print(f"   Migrated {migrated_count} documents...")
                
        except Exception as e:
            print(f"   Error migrating document {migrated_count}: {e}")
            continue
    
    # Store metadata
    sources = list(set(doc.get("source", "unknown") for doc in local_corpus if doc.get("source")))
    redis_client.hset("corpus:metadata", mapping={
        "total_documents": migrated_count,
        "last_updated": datetime.now().isoformat(),
        "urls": json.dumps(sources),
        "migration_source": "corpus_local.json"
    })
    
    print(f"✅ Migration complete! {migrated_count} documents migrated to Redis")
    print(f"📚 Sources: {sources}")
    
    return True

def test_migration():
    """Test that the migration worked by searching for our person"""
    redis_url = os.getenv("REDIS_URL", "redis://default:987654321@72.60.43.106:6379")
    redis_client = redis.from_url(redis_url, decode_responses=True)
    
    print("\n🔍 Testing migration - searching for 'Nangkil'...")
    
    doc_ids = redis_client.smembers("corpus:documents")
    found_docs = []
    
    for doc_id in doc_ids:
        doc_data = redis_client.hgetall(f"corpus:doc:{doc_id}")
        if doc_data and "nangkil" in doc_data["text"].lower():
            found_docs.append({
                "id": doc_id,
                "source": doc_data["source"],
                "text_preview": doc_data["text"][:200] + "..."
            })
    
    print(f"✅ Found {len(found_docs)} documents mentioning 'Nangkil'")
    
    for i, doc in enumerate(found_docs[:3]):
        print(f"\n{i+1}. Doc ID: {doc['id']}")
        print(f"   Source: {doc['source']}")
        print(f"   Preview: {doc['text_preview']}")
    
    # Check metadata
    metadata = redis_client.hgetall("corpus:metadata")
    print(f"\n📊 Corpus metadata:")
    print(f"   Total documents: {metadata.get('total_documents', 'N/A')}")
    print(f"   Last updated: {metadata.get('last_updated', 'N/A')}")
    print(f"   Sources: {metadata.get('urls', 'N/A')}")

def main():
    print("🚀 Migrating Local Corpus to Redis")
    print("=" * 50)
    
    if migrate_corpus_to_redis():
        test_migration()
        print("\n🎉 Migration successful! Your API should now know about Atty. Philip Ray L. Nangkil")
        print("\n🧪 Test with:")
        print('curl -X POST http://localhost:8000/ask -H "Content-Type: application/json" -d \'{"question": "Do you know Atty. Philip Ray L. Nangkil?", "user_id": "test"}\'')
    else:
        print("\n❌ Migration failed!")

if __name__ == "__main__":
    main()
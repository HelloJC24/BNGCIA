"""
Test Redis-based RAG API functionality
This script tests the Redis-only implementation
"""
import time
import requests

BASE_URL = "http://localhost:8000"

def test_redis_rag_workflow():
    """Test the complete Redis-based workflow"""
    print("🔧 Testing Redis-Based RAG API Workflow")
    print("=" * 50)
    
    try:
        # 1. Health check
        print("1. 🔍 Health Check...")
        response = requests.get(f"{BASE_URL}/")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ API is running")
            print(f"   Redis connected: {data.get('redis_connected', False)}")
        else:
            print(f"   ❌ API not available: {response.status_code}")
            return
        
        # 2. Check current corpus stats
        print("\n2. 📊 Current Corpus Stats...")
        response = requests.get(f"{BASE_URL}/corpus/stats")
        if response.status_code == 200:
            stats = response.json()
            print(f"   Documents in Redis: {stats.get('total_documents', 0)}")
            print(f"   Unique URLs: {stats.get('unique_urls', 0)}")
        
        # 3. Migrate existing local corpus to Redis
        print("\n3. 📁 Migrating Local Corpus to Redis...")
        response = requests.post(f"{BASE_URL}/migrate-corpus")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ {data['message']}")
            print(f"   Documents migrated: {data['documents_migrated']}")
        elif response.status_code == 404:
            print("   ⚠️ No local corpus found, building new one...")
            
            # Build new corpus
            print("\n4. 🚀 Building New Corpus...")
            build_payload = {
                "urls": [
                    "https://thebngc.com",
                    "https://gogel.thebngc.com",
                    "https://gogel.thebngc.com/agents",
                    "https://uptura-tech.com"
                ],
                "force_rebuild": True
            }
            
            response = requests.post(f"{BASE_URL}/prep-rag", json=build_payload)
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ {data['message']}")
                print(f"   Documents created: {data['documents_count']}")
                print(f"   URLs processed: {data['urls_processed']}")
            else:
                print(f"   ❌ Failed to build corpus: {response.status_code}")
                return
        else:
            print(f"   ❌ Migration failed: {response.status_code}")
            return
        
        # 4. Verify corpus in Redis
        print("\n5. ✅ Verifying Corpus in Redis...")
        response = requests.get(f"{BASE_URL}/corpus/stats")
        if response.status_code == 200:
            stats = response.json()
            print(f"   Total documents: {stats['total_documents']}")
            print(f"   Unique URLs: {stats['unique_urls']}")
            print(f"   Total characters: {stats['total_characters']}")
            print(f"   Average chunk size: {stats['average_chunk_size']}")
            
            if stats['total_documents'] == 0:
                print("   ❌ No documents in Redis!")
                return
        
        # 5. Test questions
        print("\n6. ❓ Testing Questions...")
        test_questions = [
            {
                "query": "What is GoGel Real Estate?",
                "user_id": "test_user@redis.com"
            },
            {
                "query": "Tell me about the agents at GoGel",
                "user_id": "test_user@redis.com"
            },
            {
                "query": "What services does Uptura Tech provide?",
                "user_id": "tech_user@redis.com"
            }
        ]
        
        for i, question in enumerate(test_questions, 1):
            print(f"\n   Question {i}: {question['query']}")
            response = requests.post(f"{BASE_URL}/ask", json=question)
            
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ Answer: {result['answer'][:100]}...")
                print(f"   Sources: {len(result['sources'])} documents")
                print(f"   Conversation ID: {result['conversation_id']}")
            else:
                print(f"   ❌ Error: {response.status_code}")
                print(f"   Detail: {response.text}")
            
            time.sleep(1)  # Be nice to the API
        
        # 6. Test conversation history
        print("\n7. 💬 Testing Conversation History...")
        user_id = "test_user@redis.com"
        response = requests.get(f"{BASE_URL}/conversation/{user_id}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Conversation history for {user_id}:")
            print(f"   Total messages: {result['count']}")
            
            for msg in result['messages'][-2:]:  # Show last 2 messages
                print(f"     {msg['role']}: {msg['content'][:80]}...")
        else:
            print(f"   ❌ Failed to get conversation: {response.status_code}")
        
        print("\n🎉 Redis-based RAG API test completed successfully!")
        
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to the API server.")
        print("Make sure Redis is running and start the server with: python main.py")
    except Exception as e:
        print(f"❌ Test failed: {e}")

def show_usage_examples():
    """Show usage examples for the Redis-based API"""
    print("\n📋 Redis-Based API Usage Examples:")
    print("-" * 40)
    
    examples = [
        {
            "title": "1. Migrate existing corpus to Redis",
            "command": "curl -X POST http://localhost:8000/migrate-corpus"
        },
        {
            "title": "2. Build new corpus in Redis",
            "command": '''curl -X POST http://localhost:8000/prep-rag \\
  -H "Content-Type: application/json" \\
  -d '{"force_rebuild": true}' '''
        },
        {
            "title": "3. Ask question (Redis-stored corpus)",
            "command": '''curl -X POST http://localhost:8000/ask \\
  -H "Content-Type: application/json" \\
  -d '{
    "query": "What services does GoGel provide?",
    "user_id": "user@example.com"
  }' '''
        },
        {
            "title": "4. Check Redis corpus stats",
            "command": "curl http://localhost:8000/corpus/stats"
        }
    ]
    
    for example in examples:
        print(f"\n{example['title']}:")
        print(f"   {example['command']}")
    
    print("\n💡 Key Benefits of Redis-based approach:")
    print("   • Persistent corpus storage across API restarts")
    print("   • Fast vector similarity search")
    print("   • Conversation history with user context")
    print("   • Scalable for multiple concurrent users")
    print("   • No dependency on local JSON files")

if __name__ == "__main__":
    test_redis_rag_workflow()
    show_usage_examples()
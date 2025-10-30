"""
API Test Script for the RAG FastAPI server
Tests the /prep-rag and /ask endpoints
"""
import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_health_check():
    """Test the health check endpoint"""
    print("🔍 Testing health check...")
    response = requests.get(f"{BASE_URL}/")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

def test_build_rag():
    """Test building the RAG corpus"""
    print("🚀 Testing RAG corpus building...")
    payload = {
        "urls": [
            "https://thebngc.com",
            "https://gogel.thebngc.com",
            "https://gogel.thebngc.com/agents",
            "https://uptura-tech.com"
        ],
        "force_rebuild": True
    }
    
    response = requests.post(f"{BASE_URL}/prep-rag", json=payload)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

def test_ask_questions():
    """Test asking questions to the RAG system"""
    print("❓ Testing questions...")
    
    questions = [
        {
            "query": "What is GoGel Real Estate?",
            "user_id": "test@example.com"
        },
        {
            "query": "Who are the agents at GoGel?",
            "user_id": "test@example.com"
        },
        {
            "query": "What services does Uptura Tech provide?",
            "user_id": "user2@example.com"
        },
        {
            "query": "How can I contact GoGel?",
            "user_id": "test@example.com"
        }
    ]
    
    for i, question in enumerate(questions, 1):
        print(f"Question {i}: {question['query']}")
        response = requests.post(f"{BASE_URL}/ask", json=question)
        
        if response.status_code == 200:
            result = response.json()
            print(f"Answer: {result['answer'][:200]}...")
            print(f"Sources: {len(result['sources'])} documents")
            print(f"Conversation ID: {result['conversation_id']}")
        else:
            print(f"Error: {response.status_code} - {response.text}")
        
        print("-" * 50)
        time.sleep(1)  # Be nice to the API

def test_conversation_history():
    """Test conversation history endpoint"""
    print("💬 Testing conversation history...")
    
    user_id = "test@example.com"
    response = requests.get(f"{BASE_URL}/conversation/{user_id}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Conversation history for {user_id}:")
        print(f"Total messages: {result['count']}")
        
        for msg in result['messages'][-3:]:  # Show last 3 messages
            print(f"  {msg['role']}: {msg['content'][:100]}...")
    else:
        print(f"Error: {response.status_code} - {response.text}")
    print()

def test_corpus_stats():
    """Test corpus statistics endpoint"""
    print("📊 Testing corpus statistics...")
    
    response = requests.get(f"{BASE_URL}/corpus/stats")
    
    if response.status_code == 200:
        stats = response.json()
        print(f"Total documents: {stats.get('total_documents', 0)}")
        print(f"Unique URLs: {stats.get('unique_urls', 0)}")
        print(f"Total characters: {stats.get('total_characters', 0)}")
        print(f"Average chunk size: {stats.get('average_chunk_size', 0)}")
        print(f"URLs: {len(stats.get('urls', []))}")
    else:
        print(f"Error: {response.status_code} - {response.text}")
    print()

def main():
    """Run all tests"""
    print("🧪 RAG API Test Suite")
    print("=" * 50)
    
    try:
        test_health_check()
        test_corpus_stats()
        
        # Uncomment the line below to build/rebuild the corpus
        # test_build_rag()
        
        test_ask_questions()
        test_conversation_history()
        
        print("✅ All tests completed!")
        
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to the API server.")
        print("Make sure the server is running with: python main.py")
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    main()
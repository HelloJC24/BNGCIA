#!/usr/bin/env python3
"""
Test rebuilding the corpus with correct URLs and then search for the person
"""
import requests
import json
import time

API_BASE = "http://localhost:8000"

def rebuild_corpus():
    """Rebuild the corpus with correct URLs"""
    print("🔨 Rebuilding corpus with correct URLs...")
    
    response = requests.post(f"{API_BASE}/prep-rag/", json={
        "urls": [
            "https://thebngc.com",
            "https://gogel.thebngc.com", 
            "https://gogel.thebngc.com/agents"
        ],
        "force_rebuild": True
    })
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ {data['message']}")
        return True
    else:
        print(f"❌ Failed: {response.text}")
        return False

def test_person_search():
    """Test searching for the specific person"""
    print("\n🔍 Testing search for Atty. Philip Ray L. Nangkil...")
    
    response = requests.post(f"{API_BASE}/ask", json={
        "question": "Do you know Atty. Philip Ray L. Nangkil?",
        "user_id": "test_user"
    })
    
    if response.status_code == 200:
        data = response.json()
        print(f"📝 Answer: {data['answer']}")
        print(f"📚 Sources: {data['sources']}")
        return data
    else:
        print(f"❌ Failed: {response.text}")
        return None

def debug_search():
    """Debug what's actually being found"""
    print("\n🔍 Debug search...")
    
    response = requests.post(f"{API_BASE}/debug-search", json={
        "question": "Philip Nangkil",
        "user_id": "debug_user"
    })
    
    if response.status_code == 200:
        data = response.json()
        print(f"📊 Total documents: {data['total_documents']}")
        
        for i, item in enumerate(data['top_similarities'][:3]):
            print(f"\n{i+1}. Similarity: {item['similarity']:.4f}")
            print(f"   Source: {item['source']}")
            print(f"   Preview: {item['text_preview']}")
    else:
        print(f"❌ Debug failed: {response.text}")

def main():
    print("🧪 Testing Atty. Philip Ray L. Nangkil Search")
    print("=" * 60)
    
    # Step 1: Rebuild corpus
    if rebuild_corpus():
        print("\n⏳ Waiting for corpus to build...")
        time.sleep(10)  # Wait for background build
        
        # Step 2: Test search
        test_person_search()
        
        # Step 3: Debug if needed
        debug_search()
    
if __name__ == "__main__":
    main()
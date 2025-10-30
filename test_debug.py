#!/usr/bin/env python3
"""
Debug the search functionality
"""
import requests
import json

API_BASE = "http://localhost:8000"

def debug_search(question):
    """Debug what content is being retrieved"""
    print(f"\n🔍 Debugging search for: '{question}'")
    print("=" * 60)
    
    try:
        response = requests.post(f"{API_BASE}/debug-search", json={
            "question": question,
            "user_id": "debug_user"
        })
        
        if response.status_code == 200:
            data = response.json()
            print(f"📊 Total documents: {data['total_documents']}")
            print(f"🎯 Top similarities:")
            
            for i, item in enumerate(data['top_similarities'][:5]):
                print(f"\n{i+1}. Similarity: {item['similarity']:.4f}")
                print(f"   Source: {item['source']}")
                print(f"   Preview: {item['text_preview']}")
                print("-" * 40)
                
        else:
            print(f"❌ Status: {response.status_code}")
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    print("🔍 Debug RAG Search")
    
    # Test the specific question
    debug_search("Do you know Atty. Philip Ray L. Nangkil?")
    
    # Test a simpler search
    debug_search("Philip Nangkil")
    
    # Test something that should definitely be there
    debug_search("real estate")

if __name__ == "__main__":
    main()
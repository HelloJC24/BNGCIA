#!/usr/bin/env python3
"""
Test migration via API endpoint
"""
import requests
import json

API_BASE = "http://localhost:8000"

def test_migration_endpoint():
    """Test the migration endpoint"""
    print("🚀 Testing corpus migration via API...")
    
    try:
        response = requests.post(f"{API_BASE}/migrate-corpus")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Migration successful!")
            print(f"📊 Documents migrated: {data['documents_migrated']}")
            print(f"📚 Sources: {data['sources']}")
            print(f"💬 Message: {data['message']}")
            return True
        else:
            print(f"❌ Migration failed: {response.status_code}")
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_person_search():
    """Test searching for the person after migration"""
    print("\n🔍 Testing search for Atty. Philip Ray L. Nangkil...")
    
    try:
        response = requests.post(f"{API_BASE}/ask", json={
            "question": "Tell me about Atty. Philip Ray L. Nangkil",
            "user_id": "test_user"
        })
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Search successful!")
            print(f"📝 Answer: {data['answer']}")
            print(f"📚 Sources: {data['sources']}")
            
            # Check if the answer contains the person's info
            if "nangkil" in data['answer'].lower() and "broker" in data['answer'].lower():
                print("🎉 SUCCESS: The AI now knows about Atty. Philip Ray L. Nangkil!")
            else:
                print("⚠️ The person might still not be found in the corpus")
                
        else:
            print(f"❌ Search failed: {response.status_code}")
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def test_debug_search():
    """Debug what's in the corpus"""
    print("\n🔍 Debug search for 'Nangkil'...")
    
    try:
        response = requests.post(f"{API_BASE}/debug-search", json={
            "question": "Nangkil",
            "user_id": "debug"
        })
        
        if response.status_code == 200:
            data = response.json()
            print(f"📊 Total documents: {data['total_documents']}")
            
            nangkil_found = False
            for item in data['top_similarities'][:5]:
                if 'nangkil' in item['text_preview'].lower():
                    nangkil_found = True
                    print(f"✅ Found Nangkil mention:")
                    print(f"   Similarity: {item['similarity']:.4f}")
                    print(f"   Source: {item['source']}")
                    print(f"   Preview: {item['text_preview'][:300]}...")
                    break
            
            if not nangkil_found:
                print("❌ No Nangkil mentions found in top results")
                
        else:
            print(f"❌ Debug failed: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    print("🧪 Testing Corpus Migration and Search")
    print("=" * 60)
    
    # Step 1: Migrate corpus
    if test_migration_endpoint():
        # Step 2: Test search
        test_person_search()
        
        # Step 3: Debug if needed
        test_debug_search()
    else:
        print("\n💡 If migration failed, the API might not be running.")
        print("   Start the API first with: python main_basic.py")

if __name__ == "__main__":
    main()
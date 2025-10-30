#!/usr/bin/env python3
"""
Test the improved conversational AI responses
"""
import requests
import json

API_BASE = "http://localhost:8000"

def test_endpoint(question, expected_type):
    """Test a question and print the response"""
    print(f"\n🔍 Testing: '{question}'")
    print(f"Expected: {expected_type}")
    print("-" * 50)
    
    try:
        response = requests.post(f"{API_BASE}/ask", json={
            "question": question,
            "user_id": "test_user"
        })
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Status: {response.status_code}")
            print(f"📝 Answer: {data['answer']}")
            print(f"📚 Sources: {data['sources']}")
        else:
            print(f"❌ Status: {response.status_code}")
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    print("🤖 Testing Improved Conversational AI")
    print("=" * 60)
    
    # Test greetings
    test_endpoint("Hello!", "Natural greeting response")
    test_endpoint("Hi there", "Natural greeting response") 
    test_endpoint("Good morning", "Natural greeting response")
    test_endpoint("How are you?", "Natural greeting response")
    
    # Test company questions
    test_endpoint("What services do you offer?", "Context-based answer")
    test_endpoint("Tell me about the company", "Context-based answer")
    test_endpoint("What is your company about?", "Context-based answer")
    
    # Test edge cases
    test_endpoint("What's the weather like?", "Graceful no-info response")
    test_endpoint("Do you sell unicorns?", "Graceful no-info response")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Test OpenAI client initialization
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

try:
    from openai import OpenAI
    print("✅ OpenAI import successful")
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not found in environment")
        sys.exit(1)
    
    print("✅ API key found")
    
    # Test client initialization
    client = OpenAI(api_key=api_key)
    print("✅ OpenAI client initialized successfully")
    
    # Test a simple API call
    try:
        response = client.embeddings.create(
            input="test",
            model="text-embedding-3-small"
        )
        print(f"✅ API call successful - embedding dimension: {len(response.data[0].embedding)}")
    except Exception as e:
        print(f"❌ API call failed: {e}")
        sys.exit(1)
    
    print("🎉 All tests passed - OpenAI client is working!")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    sys.exit(1)
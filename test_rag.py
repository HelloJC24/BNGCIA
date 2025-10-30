#!/usr/bin/env python3
"""
Test script for the improved RAG implementation
"""
import os
import sys
from rag_website import (
    load_local_corpus, 
    answer_with_context, 
    get_corpus_stats, 
    search_corpus,
    build_corpus_from_urls,
    DEFAULT_URLS
)

def test_rag_system():
    """Test the RAG system with various questions."""
    print("🚀 Testing Improved Local RAG System")
    print("=" * 50)
    
    # Load corpus
    corpus_file = "corpus_local.json"
    if not os.path.exists(corpus_file):
        print(f"⚠️ Corpus file {corpus_file} not found. Building new corpus...")
        corpus = build_corpus_from_urls(DEFAULT_URLS)
        if not corpus:
            print("❌ Failed to build corpus. Exiting.")
            return
    else:
        corpus = load_local_corpus(corpus_file)
    
    if not corpus:
        print("❌ No corpus available. Exiting.")
        return
    
    # Show corpus stats
    stats = get_corpus_stats(corpus)
    print(f"\n📊 Corpus Statistics:")
    print(f"   • Total documents: {stats['total_docs']}")
    print(f"   • Unique URLs: {stats['unique_urls']}")
    print(f"   • Average chunk size: {stats['avg_chunk_size']} characters")
    print(f"   • Total characters: {stats['total_characters']}")
    
    # Test questions
    test_questions = [
        "What is GoGel Real Estate?",
        "What services does Uptura Tech provide?",
        "How many years of experience does GoGel have?",
        "What is the address or contact information for GoGel?",
        "What technology does Uptura Tech specialize in?",
    ]
    
    print(f"\n🔍 Testing RAG with {len(test_questions)} questions:")
    print("-" * 50)
    
    for i, question in enumerate(test_questions, 1):
        print(f"\n{i}. Question: {question}")
        try:
            result = answer_with_context(question, corpus)
            print(f"   Answer: {result['answer'][:200]}...")
            print(f"   Sources: {len(result['retrieved'])} relevant documents found")
            if result['retrieved']:
                best_source = result['retrieved'][0]
                print(f"   Best match: {best_source['url']} (score: {best_source['score']:.3f})")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    # Test search functionality
    print(f"\n🔎 Testing search functionality:")
    search_terms = ["real estate", "technology", "AI", "properties"]
    
    for term in search_terms:
        results = search_corpus(corpus, term, max_results=3)
        print(f"   • '{term}': {len(results)} results found")
    
    print(f"\n✅ Testing complete!")

if __name__ == "__main__":
    test_rag_system()
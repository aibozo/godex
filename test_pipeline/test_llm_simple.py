#!/usr/bin/env python3
"""
Test basic LLM functionality.
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
os.chdir(Path(__file__).parent.parent)

from agent.llm import LLMClient


def test_basic_llm():
    print("Testing basic LLM functionality...")
    
    # Create LLM client
    llm = LLMClient(model="gemini-2.5-flash-preview-05-20")
    
    # Simple test
    try:
        response = llm.chat_completion([
            {"role": "user", "content": "Say 'Hello, I am working!' in exactly 5 words."}
        ], temperature=0.1, max_tokens=50)
        
        print(f"✅ LLM Response: {response}")
        
    except Exception as e:
        print(f"❌ LLM Error: {e}")
        
    # Test JSON generation
    try:
        print("\nTesting JSON generation...")
        response = llm.chat_completion([
            {"role": "user", "content": 'Return this exact JSON: {"status": "ok", "value": 42}'}
        ], temperature=0, max_tokens=50)
        
        print(f"✅ JSON Response: {response}")
        
    except Exception as e:
        print(f"❌ JSON Error: {e}")


if __name__ == "__main__":
    test_basic_llm()
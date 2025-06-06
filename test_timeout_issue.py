#!/usr/bin/env python3
"""Test if Gemini API call is blocking."""

import sys
sys.path.insert(0, '.')

import time
import google.generativeai as genai
import os

def test_direct_gemini():
    """Test Gemini API directly."""
    print("Testing direct Gemini API call...")
    
    # Configure Gemini
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
    
    # Use the full model name that our agents use
    model_name = "gemini-2.5-flash-preview-05-20"
    print(f"Creating model with name: {model_name}")
    model = genai.GenerativeModel(model_name)
    
    start = time.time()
    print("Calling generate_content...")
    
    try:
        response = model.generate_content(
            "Say hello world",
            generation_config={"temperature": 0.3, "max_output_tokens": 100}
        )
        
        elapsed = time.time() - start
        print(f"Response received in {elapsed:.2f}s: {response.text}")
        
    except Exception as e:
        elapsed = time.time() - start
        print(f"Error after {elapsed:.2f}s: {e}")

if __name__ == "__main__":
    test_direct_gemini()
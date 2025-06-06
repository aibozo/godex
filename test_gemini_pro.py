#!/usr/bin/env python3
"""Test Gemini 2.5 Pro - a paid-only model."""

import sys
sys.path.insert(0, '.')

from agent.core.base_agent import BaseAgent
import time

class TestProAgent(BaseAgent):
    def __init__(self):
        # Use Gemini 2.5 Pro which has NO free tier
        super().__init__(model="gemini-2.5-pro-preview-06-05", component="planner")
    
    def handle_request(self, message):
        return {"status": "ok"}
    
    def test_paid_tier(self):
        """Test that we can use a paid-only model."""
        print("=== Testing Gemini 2.5 Pro (Paid-Only Model) ===\n")
        
        try:
            print("Making API call to Gemini 2.5 Pro...")
            start = time.time()
            
            response = self.chat_completion([
                {"role": "user", "content": "Say 'Hello from Gemini 2.5 Pro' and nothing else"}
            ], temperature=0, max_tokens=10000)
            
            elapsed = time.time() - start
            print(f"\n✅ SUCCESS! Response received in {elapsed:.2f}s:")
            print(f"Response: {response}")
            print("\nThis confirms we're using the PAID API since Gemini 2.5 Pro has no free tier!")
            
            # Get usage stats
            status = self.get_status()
            print(f"\nAgent Status: {status}")
            
            return True
            
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            print("\nIf you see a quota error, it means:")
            print("1. The API key might still be on free tier")
            print("2. You may need to generate a new API key after enabling billing")
            print("3. Billing activation might still be pending (can take up to an hour)")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    agent = TestProAgent()
    success = agent.test_paid_tier()
    
    if not success:
        print("\n💡 Troubleshooting tips:")
        print("1. Check that billing is enabled in Google AI Studio")
        print("2. Try generating a NEW API key AFTER enabling billing")
        print("3. Wait 30-60 minutes for billing to fully activate")
        print("4. Verify the API key is set in your environment")
        print("\n🔑 The most common fix: Generate a fresh API key!")
        print("   Go to: https://aistudio.google.com/app/apikey")
        print("   Delete the old key and create a new one after billing is enabled")
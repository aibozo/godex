#!/usr/bin/env python3
"""Test rapid API calls to check if we hit free tier limits."""

import sys
sys.path.insert(0, '.')

from agent.core.base_agent import BaseAgent
import time

class TestRapidAgent(BaseAgent):
    def __init__(self):
        super().__init__(model="gemini-2.5-pro-preview-06-05", component="planner")
    
    def handle_request(self, message):
        return {"status": "ok"}

def test_rapid_calls():
    """Make 15 rapid API calls (exceeds free tier limit of 10/minute)."""
    print("=== Testing Rapid API Calls (15 requests) ===\n")
    print("Free tier limit: 10 requests/minute")
    print("If we're on paid tier, all should succeed.\n")
    
    agent = TestRapidAgent()
    
    success = 0
    free_tier_errors = 0
    
    for i in range(15):
        print(f"Request {i+1}/15: ", end="", flush=True)
        try:
            start = time.time()
            response = agent.chat_completion([
                {"role": "user", "content": f"Say 'Response {i+1}' and nothing else"}
            ], temperature=0, max_tokens=100)
            elapsed = time.time() - start
            print(f"✅ Success in {elapsed:.2f}s - {response}")
            success += 1
            
        except Exception as e:
            error_str = str(e)
            if "free_tier" in error_str.lower() or "FreeTier" in error_str:
                print(f"❌ FREE TIER ERROR!")
                free_tier_errors += 1
                if i == 0:  # Print full error for first occurrence
                    print(f"   Full error: {error_str}")
            else:
                print(f"❌ Error: {error_str[:80]}...")
            
        # Small delay to avoid overwhelming the API
        time.sleep(0.5)
    
    print(f"\n{'='*50}")
    print(f"RESULTS:")
    print(f"  Successful calls: {success}/15")
    print(f"  Free tier errors: {free_tier_errors}")
    
    if free_tier_errors > 0:
        print(f"\n❌ STILL ON FREE TIER - Got {free_tier_errors} quota errors")
        print("Need to regenerate API key or wait for billing to activate")
    else:
        print(f"\n✅ PAID TIER CONFIRMED - All {success} calls succeeded!")

if __name__ == "__main__":
    test_rapid_calls()
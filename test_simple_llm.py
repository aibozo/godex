#!/usr/bin/env python3
"""Test simple LLM call to verify environment."""

import sys
sys.path.insert(0, '.')

from agent.core.base_agent import BaseAgent

class TestAgent(BaseAgent):
    def __init__(self):
        super().__init__(model="gemini-2.5-flash-preview-05-20", component="planner")
    
    def handle_request(self, message):
        return {"status": "ok"}
    
    def test_llm(self):
        print("Testing LLM call...")
        try:
            response = self.chat_completion([
                {"role": "user", "content": "Say 'hello world' and nothing else"}
            ], temperature=0, max_tokens=100)
            print(f"Response: {response}")
            return response
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            return None

if __name__ == "__main__":
    agent = TestAgent()
    agent.test_llm()
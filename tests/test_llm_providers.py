# Test all LLM providers
import os
import pytest
from dotenv import load_dotenv

load_dotenv()

from agent.llm import LLMClient

# Skip tests if API keys not available
OPENAI_KEY = os.environ.get('OPENAI_API_KEY')
ANTHROPIC_KEY = os.environ.get('ANTHROPIC_API_KEY') 
GEMINI_KEY = os.environ.get('GEMINI_API_KEY')

@pytest.mark.skipif(not OPENAI_KEY, reason="OPENAI_API_KEY not set")
def test_openai_provider():
    """Test OpenAI provider"""
    client = LLMClient("gpt-4o", component="test")
    
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Say 'Hello OpenAI!' and nothing else."}
    ]
    
    response = client.chat_completion(messages)
    assert response
    assert "OpenAI" in response or "openai" in response.lower()

@pytest.mark.skipif(not ANTHROPIC_KEY, reason="ANTHROPIC_API_KEY not set")
def test_anthropic_provider():
    """Test Anthropic provider"""
    client = LLMClient("claude-3.5-sonnet-20241022", component="test")
    
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Say 'Hello Claude!' and nothing else."}
    ]
    
    response = client.chat_completion(messages)
    assert response
    assert "Claude" in response or "claude" in response.lower()

@pytest.mark.skipif(not GEMINI_KEY, reason="GEMINI_API_KEY not set")
def test_gemini_provider():
    """Test Google Gemini provider"""
    client = LLMClient("gemini-2.5-flash-preview-05-20", component="test")
    
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Say 'Hello Gemini!' and nothing else."}
    ]
    
    response = client.chat_completion(messages)
    assert response
    assert "Gemini" in response or "gemini" in response.lower()

def test_cost_tracking_integration(tmp_path, monkeypatch):
    """Test that cost tracking works with real API calls"""
    if not GEMINI_KEY:
        pytest.skip("GEMINI_API_KEY not set")
    
    # Use temp database
    monkeypatch.setenv("AGENT_HOME", str(tmp_path))
    (tmp_path / "memory").mkdir()
    
    client = LLMClient("gemini-1.5-flash", component="test")
    
    # Get initial cost
    initial_cost = client.usage_tracker.get_today_cost()
    
    # Make a call
    messages = [
        {"role": "user", "content": "Count to 5"}
    ]
    
    response = client.chat_completion(messages, task_id="TEST-1")
    assert response
    
    # Check cost was tracked
    new_cost = client.usage_tracker.get_today_cost()
    assert new_cost > initial_cost
    
    # Check task tracking
    task_cost, input_tokens, output_tokens = client.usage_tracker.get_usage_by_task("TEST-1")
    assert task_cost > 0
    assert input_tokens > 0
    assert output_tokens > 0
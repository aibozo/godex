# Test cost tracking and model registry
import pytest
from datetime import date
from pathlib import Path

from agent.models import (
    get_model_info, 
    calculate_cost,
    list_models_by_provider,
    list_models_by_capability,
    UsageTracker
)

def test_model_registry():
    """Test that model registry has expected models"""
    # Check key models exist
    assert get_model_info("gpt-4o") is not None
    assert get_model_info("claude-3.5-sonnet-20241022") is not None
    assert get_model_info("gemini-2.5-flash-preview-05-20") is not None
    
    # Check unknown model
    assert get_model_info("fake-model-123") is None

def test_cost_calculation():
    """Test cost calculations for different models"""
    # GPT-4o: $2.50/$10 per 1M tokens
    cost = calculate_cost("gpt-4o", input_tokens=1000, output_tokens=500)
    expected = (2.50 * 1000 / 1_000_000) + (10.0 * 500 / 1_000_000)
    assert abs(cost - expected) < 0.0001
    
    # Test thinking mode (o1 model)
    cost_normal = calculate_cost("o1", input_tokens=1000, output_tokens=500, thinking_mode=False)
    cost_thinking = calculate_cost("o1", input_tokens=1000, output_tokens=500, thinking_mode=True)
    # For o1, thinking costs are same as normal
    assert cost_normal == cost_thinking

def test_model_filtering():
    """Test filtering models by capabilities"""
    # Get all OpenAI models
    openai_models = list_models_by_provider("openai")
    assert "gpt-4o" in openai_models
    assert "o1" in openai_models
    assert "gemini-1.5-flash" not in openai_models
    
    # Get models that support thinking
    thinking_models = list_models_by_capability(supports_thinking=True)
    assert "o1" in thinking_models
    assert "o1-mini" in thinking_models
    assert "gemini-2.0-flash-thinking-exp" in thinking_models
    
    # Get models with large context
    large_context_models = list_models_by_capability(min_context=1_000_000)
    assert "gemini-1.5-pro" in large_context_models
    assert "gemini-1.5-flash" in large_context_models

def test_usage_tracker(tmp_path):
    """Test usage tracking and persistence"""
    db_path = tmp_path / "test_usage.db"
    tracker = UsageTracker(db_path)
    
    # Track some usage
    record1 = tracker.track_usage(
        model_id="gpt-4o",
        input_tokens=1000,
        output_tokens=500,
        task_id="T-1",
        component="planner"
    )
    
    assert record1.cost > 0
    assert record1.model_id == "gpt-4o"
    assert record1.provider == "openai"
    
    # Track more usage
    record2 = tracker.track_usage(
        model_id="gemini-1.5-flash",
        input_tokens=2000,
        output_tokens=1000,
        task_id="T-1",
        component="executor"
    )
    
    # Check today's cost
    today_cost = tracker.get_today_cost()
    assert today_cost == record1.cost + record2.cost
    
    # Check task usage
    task_cost, task_input, task_output = tracker.get_usage_by_task("T-1")
    assert task_cost == record1.cost + record2.cost
    assert task_input == 3000
    assert task_output == 1500
    
    # Check daily usage
    daily = tracker.get_usage_by_date(date.today())
    assert daily.total_cost == today_cost
    assert daily.total_input_tokens == 3000
    assert daily.total_output_tokens == 1500
    assert "gpt-4o" in daily.model_breakdown
    assert "gemini-1.5-flash" in daily.model_breakdown

def test_cost_cap_enforcement(tmp_path, monkeypatch):
    """Test that cost cap is enforced"""
    db_path = tmp_path / "test_usage.db"
    tracker = UsageTracker(db_path)
    
    # Set a very low cost cap
    monkeypatch.setattr(tracker.settings, "cost_cap_daily", 0.01)
    
    # First usage should work
    tracker.track_usage(
        model_id="gpt-4o",
        input_tokens=100,
        output_tokens=50,
        component="test"
    )
    
    # Second usage should fail (exceeds cap)
    with pytest.raises(ValueError, match="Daily cost cap"):
        tracker.track_usage(
            model_id="gpt-4o",
            input_tokens=10000,
            output_tokens=5000,
            component="test"
        )

def test_usage_report(tmp_path):
    """Test usage report generation"""
    db_path = tmp_path / "test_usage.db"
    tracker = UsageTracker(db_path)
    
    # Track some usage
    tracker.track_usage("gpt-4o", 1000, 500, component="planner")
    tracker.track_usage("gemini-1.5-flash", 2000, 1000, component="executor")
    
    # Get report
    report = tracker.get_usage_report(days=1)
    
    assert "LLM Usage Report" in report
    assert date.today().isoformat() in report
    assert "gpt-4o" in report
    assert "gemini-1.5-flash" in report
    assert "Total Cost:" in report
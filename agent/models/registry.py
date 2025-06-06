# Model registry with cost information and capabilities
from typing import Dict, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime

Provider = Literal["openai", "anthropic", "google"]

class ModelInfo(BaseModel):
    """Information about a specific model"""
    name: str
    provider: Provider
    
    # Cost per million tokens
    input_cost: float = Field(..., description="Cost per 1M input tokens in USD")
    output_cost: float = Field(..., description="Cost per 1M output tokens in USD")
    
    # For models with thinking/reasoning mode
    thinking_input_cost: Optional[float] = Field(None, description="Cost per 1M input tokens with thinking")
    thinking_output_cost: Optional[float] = Field(None, description="Cost per 1M output tokens with thinking")
    
    # Capabilities
    context_window: int = Field(..., description="Maximum context window in tokens")
    max_output_tokens: int = Field(4096, description="Maximum output tokens")
    supports_tools: bool = Field(True, description="Whether model supports function/tool calling")
    supports_thinking: bool = Field(False, description="Whether model has thinking/reasoning mode")
    supports_vision: bool = Field(False, description="Whether model supports image inputs")
    
    # Performance hints
    is_fast: bool = Field(True, description="Whether this is a fast/low-latency model")
    recommended_for: list[str] = Field(default_factory=list, description="Recommended use cases")

# Model Registry
MODELS: Dict[str, ModelInfo] = {
    # Anthropic Models
    "claude-opus-4-20250514": ModelInfo(
        name="Claude Opus 4",
        provider="anthropic",
        input_cost=15.0,  # $15/1M tokens
        output_cost=75.0,  # $75/1M tokens
        context_window=200000,
        supports_tools=True,
        supports_vision=True,
        is_fast=False,
        recommended_for=["complex_reasoning", "code_generation", "analysis"]
    ),
    
    "claude-3.5-sonnet-20241022": ModelInfo(
        name="Claude 3.5 Sonnet",
        provider="anthropic", 
        input_cost=3.0,   # $3/1M tokens
        output_cost=15.0,  # $15/1M tokens
        context_window=200000,
        supports_tools=True,
        supports_vision=True,
        is_fast=True,
        recommended_for=["general", "code_generation", "chat"]
    ),
    
    "claude-sonnet-4-20250514": ModelInfo(
        name="Claude Sonnet 4",
        provider="anthropic",
        input_cost=3.0,   # $3/1M tokens (estimated)
        output_cost=15.0,  # $15/1M tokens (estimated)
        context_window=200000,
        supports_tools=True,
        supports_vision=True,
        is_fast=True,
        recommended_for=["executor", "code_generation", "tool_calling"]
    ),
    
    # OpenAI Models
    "gpt-4o": ModelInfo(
        name="GPT-4o",
        provider="openai",
        input_cost=2.50,  # $2.50/1M tokens
        output_cost=10.0,  # $10/1M tokens
        context_window=128000,
        supports_tools=True,
        supports_vision=True,
        is_fast=True,
        recommended_for=["general", "code_generation", "multimodal"]
    ),
    
    "o1": ModelInfo(
        name="OpenAI o1",
        provider="openai",
        input_cost=15.0,  # $15/1M tokens
        output_cost=60.0,  # $60/1M tokens
        thinking_input_cost=15.0,  # Same as regular for o1
        thinking_output_cost=60.0,
        context_window=200000,
        max_output_tokens=100000,
        supports_tools=False,  # o1 doesn't support tools yet
        supports_thinking=True,
        is_fast=False,
        recommended_for=["complex_reasoning", "math", "science"]
    ),
    
    "o1-mini": ModelInfo(
        name="OpenAI o1-mini", 
        provider="openai",
        input_cost=3.0,   # $3/1M tokens
        output_cost=12.0,  # $12/1M tokens
        thinking_input_cost=3.0,
        thinking_output_cost=12.0,
        context_window=128000,
        max_output_tokens=65536,
        supports_tools=False,
        supports_thinking=True,
        is_fast=True,
        recommended_for=["reasoning", "code_generation"]
    ),
    
    "o3-mini": ModelInfo(
        name="OpenAI o3-mini",
        provider="openai",
        input_cost=5.0,   # Estimated - adjust when released
        output_cost=20.0,  # Estimated
        context_window=128000,
        supports_tools=True,
        is_fast=True,
        recommended_for=["general", "fast_reasoning"]
    ),
    
    # Google Gemini Models
    "gemini-1.5-pro": ModelInfo(
        name="Gemini 1.5 Pro",
        provider="google",
        input_cost=1.25,  # $1.25/1M tokens (up to 128k)
        output_cost=5.0,   # $5/1M tokens (up to 128k)
        context_window=2000000,  # 2M token context
        supports_tools=True,
        supports_vision=True,
        is_fast=False,
        recommended_for=["long_context", "analysis", "multimodal"]
    ),
    
    "gemini-1.5-flash": ModelInfo(
        name="Gemini 1.5 Flash",
        provider="google",
        input_cost=0.075,  # $0.075/1M tokens (up to 128k)
        output_cost=0.30,   # $0.30/1M tokens (up to 128k)
        context_window=1000000,  # 1M token context
        supports_tools=True,
        supports_vision=True,
        is_fast=True,
        recommended_for=["general", "fast_responses", "high_volume"]
    ),
    
    "gemini-2.0-flash-exp": ModelInfo(
        name="Gemini 2.0 Flash Experimental",
        provider="google",
        input_cost=0.10,   # Estimated pricing
        output_cost=0.40,   # Estimated pricing
        context_window=1000000,
        supports_tools=True,
        supports_vision=True,
        is_fast=True,
        recommended_for=["experimental", "tool_use"]
    ),
    
    "gemini-2.0-flash-thinking-exp": ModelInfo(
        name="Gemini 2.0 Flash Thinking",
        provider="google",
        input_cost=0.10,
        output_cost=0.40,
        thinking_input_cost=0.15,  # Estimated premium for thinking
        thinking_output_cost=0.60,
        context_window=32768,
        supports_tools=True,
        supports_thinking=True,
        is_fast=True,
        recommended_for=["reasoning", "planning"]
    ),
    
    "gemini-2.5-pro-preview-06-05": ModelInfo(
        name="Gemini 2.5 Pro Preview",
        provider="google",
        input_cost=2.50,   # Premium model pricing
        output_cost=10.0,
        thinking_input_cost=3.75,  # With thinking mode
        thinking_output_cost=15.0,
        context_window=2000000,
        supports_tools=True,
        supports_thinking=True,
        supports_vision=True,
        is_fast=False,
        recommended_for=["complex_tasks", "best_quality"]
    ),
    
    "gemini-2.5-flash-preview-05-20": ModelInfo(
        name="Gemini 2.5 Flash Preview", 
        provider="google",
        input_cost=0.60,   # $0.60/1M tokens
        output_cost=2.40,   # $2.40/1M tokens
        context_window=1000000,
        supports_tools=True,
        supports_vision=True,
        is_fast=True,
        recommended_for=["tool_calling", "executor", "general"]
    ),
}

def get_model_info(model_id: str) -> Optional[ModelInfo]:
    """Get model information by ID"""
    return MODELS.get(model_id)

def calculate_cost(
    model_id: str, 
    input_tokens: int, 
    output_tokens: int,
    thinking_mode: bool = False
) -> float:
    """Calculate cost for a specific model usage"""
    model = get_model_info(model_id)
    if not model:
        raise ValueError(f"Unknown model: {model_id}")
    
    if thinking_mode and model.supports_thinking:
        input_cost = (model.thinking_input_cost or model.input_cost) * input_tokens / 1_000_000
        output_cost = (model.thinking_output_cost or model.output_cost) * output_tokens / 1_000_000
    else:
        input_cost = model.input_cost * input_tokens / 1_000_000
        output_cost = model.output_cost * output_tokens / 1_000_000
    
    return input_cost + output_cost

def list_models_by_provider(provider: Provider) -> list[str]:
    """List all model IDs for a specific provider"""
    return [
        model_id for model_id, model in MODELS.items() 
        if model.provider == provider
    ]

def list_models_by_capability(
    supports_tools: Optional[bool] = None,
    supports_thinking: Optional[bool] = None,
    supports_vision: Optional[bool] = None,
    min_context: Optional[int] = None
) -> list[str]:
    """List models matching specific capabilities"""
    results = []
    for model_id, model in MODELS.items():
        if supports_tools is not None and model.supports_tools != supports_tools:
            continue
        if supports_thinking is not None and model.supports_thinking != supports_thinking:
            continue
        if supports_vision is not None and model.supports_vision != supports_vision:
            continue
        if min_context is not None and model.context_window < min_context:
            continue
        results.append(model_id)
    return results
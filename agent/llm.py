# agent/llm.py - LLM abstraction for multiple providers

import os
from typing import List, Dict, Any, Optional, Tuple
from openai import OpenAI
import google.generativeai as genai
import anthropic
from agent.config import get_settings
from agent.models import get_model_info, UsageTracker


class LLMClient:
    """Unified interface for different LLM providers"""
    
    def __init__(self, model: Optional[str] = None, component: Optional[str] = None):
        self.settings = get_settings()
        self.model = model or self.settings.model_router_default
        self.component = component  # Track which component is using this (planner, executor, etc.)
        
        # Get model info from registry
        self.model_info = get_model_info(self.model)
        if not self.model_info:
            raise ValueError(f"Unknown model: {self.model}")
        
        self.provider = self.model_info.provider
        self.thinking_mode = False  # Will be set per request
        
        # Initialize usage tracker
        self.usage_tracker = UsageTracker()
        
        # Initialize provider-specific clients
        if self.provider == "openai":
            if not self.settings.openai_api_key:
                raise ValueError("OpenAI API key not configured")
            self.openai_client = OpenAI(api_key=self.settings.openai_api_key)
                
        elif self.provider == "google":
            genai.configure(api_key=self.settings.gemini_api_key)
            if not self.settings.gemini_api_key:
                raise ValueError("Gemini API key not configured")
            self.gemini_model = genai.GenerativeModel(self.model)
            
        elif self.provider == "anthropic":
            if not self.settings.anthropic_api_key:
                raise ValueError("Anthropic API key not configured")
            self.anthropic_client = anthropic.Anthropic(api_key=self.settings.anthropic_api_key)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")
    
    def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        Send chat completion request and return content.
        Messages format: [{"role": "system"|"user"|"assistant", "content": "..."}]
        """
        task_id = kwargs.get("task_id", None)
        thinking_mode = kwargs.get("thinking_mode", False)
        
        if self.provider == "openai":
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=kwargs.get("temperature", 0.2),
                max_tokens=kwargs.get("max_tokens", self.model_info.max_output_tokens)
            )
            
            # Extract token usage
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            
            # Track usage
            self._track_usage(input_tokens, output_tokens, thinking_mode, task_id)
            
            return response.choices[0].message.content.strip()
            
        elif self.provider == "google":
            # Convert OpenAI-style messages to Gemini format
            prompt = self._convert_to_gemini_prompt(messages)
            
            generation_config = {
                "temperature": kwargs.get("temperature", 0.2),
                "max_output_tokens": kwargs.get("max_tokens", self.model_info.max_output_tokens),
            }
            
            # Add thinking mode configuration if enabled
            if thinking_mode and self.model_info.supports_thinking:
                generation_config["temperature"] = kwargs.get("temperature", 0.1)  # Lower temp for reasoning
            
            response = self.gemini_model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            # Handle different response scenarios
            if not response.candidates:
                raise RuntimeError("No candidates in Gemini response")
            
            candidate = response.candidates[0]
            
            # Check finish reason
            if candidate.finish_reason.name == "MAX_TOKENS":
                # Still return partial content if available
                if candidate.content and candidate.content.parts:
                    content = candidate.content.parts[0].text.strip()
                else:
                    raise RuntimeError("Response exceeded max tokens with no content")
            else:
                # Normal case - use text accessor
                content = response.text.strip()
            
            # Extract token usage from Gemini response
            if hasattr(response, 'usage_metadata'):
                input_tokens = response.usage_metadata.prompt_token_count
                output_tokens = response.usage_metadata.candidates_token_count
            else:
                # Estimate if not available
                input_tokens = self._estimate_tokens(prompt)
                output_tokens = self._estimate_tokens(content)
            
            # Track usage
            self._track_usage(input_tokens, output_tokens, thinking_mode, task_id)
            
            return content
        
        elif self.provider == "anthropic":
            # Convert messages to Anthropic format
            system_message = None
            anthropic_messages = []
            
            for msg in messages:
                if msg["role"] == "system":
                    system_message = msg["content"]
                else:
                    anthropic_messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
            
            # Call Anthropic API
            response = self.anthropic_client.messages.create(
                model=self.model,
                messages=anthropic_messages,
                system=system_message,
                temperature=kwargs.get("temperature", 0.2),
                max_tokens=kwargs.get("max_tokens", self.model_info.max_output_tokens)
            )
            
            # Extract usage info
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            
            # Track usage
            self._track_usage(input_tokens, output_tokens, thinking_mode, task_id)
            
            return response.content[0].text
    
    def _convert_to_gemini_prompt(self, messages: List[Dict[str, str]]) -> str:
        """Convert OpenAI-style messages to a single prompt for Gemini"""
        prompt_parts = []
        
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            
            if role == "system":
                prompt_parts.append(f"Instructions: {content}")
            elif role == "user":
                prompt_parts.append(f"User: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")
        
        return "\n\n".join(prompt_parts)
    
    def _track_usage(
        self, 
        input_tokens: int, 
        output_tokens: int, 
        thinking_mode: bool = False,
        task_id: Optional[str] = None
    ):
        """Track token usage and cost"""
        try:
            self.usage_tracker.track_usage(
                model_id=self.model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                thinking_mode=thinking_mode,
                task_id=task_id,
                component=self.component
            )
        except ValueError as e:
            # Cost cap exceeded
            raise RuntimeError(f"Cost limit exceeded: {e}")
    
    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation (4 chars per token average)"""
        return len(text) // 4
    
    def get_usage_summary(self) -> str:
        """Get a summary of recent usage"""
        return self.usage_tracker.get_usage_report(days=7)
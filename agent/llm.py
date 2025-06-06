# agent/llm.py - LLM abstraction for multiple providers

import os
import json
from typing import List, Dict, Any, Optional, Tuple
from openai import OpenAI
import google.generativeai as genai
import anthropic
from agent.config import get_settings
from agent.models import get_model_info, UsageTracker
from agent.utils.llm_logger import get_llm_logger


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
        
        # Initialize logger
        self.logger = get_llm_logger()
        
        # Initialize provider-specific clients
        if self.provider == "openai":
            if not self.settings.openai_api_key:
                raise ValueError("OpenAI API key not configured")
            self.openai_client = OpenAI(api_key=self.settings.openai_api_key)
                
        elif self.provider == "google":
            if not self.settings.gemini_api_key:
                raise ValueError("Gemini API key not configured")
            
            # Configure with API key (this should use paid tier if billing is enabled)
            genai.configure(api_key=self.settings.gemini_api_key)
            
            # Log the configuration for debugging
            print(f"[LLM] Configuring Gemini with model: {self.model}")
            
            self.gemini_model = genai.GenerativeModel(self.model)
            
        elif self.provider == "anthropic":
            if not self.settings.anthropic_api_key:
                raise ValueError("Anthropic API key not configured")
            self.anthropic_client = anthropic.Anthropic(api_key=self.settings.anthropic_api_key)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")
    
    def chat_completion(self, messages: List[Dict[str, Any]], **kwargs) -> Any:
        """
        Send chat completion request and return content or tool calls.
        Messages format: [{"role": "system"|"user"|"assistant", "content": "..."}]
        
        Returns:
            - str: If no tool calls requested
            - object with tool_calls attribute: If tools provided and LLM wants to use them
        """
        task_id = kwargs.get("task_id", None)
        thinking_mode = kwargs.get("thinking_mode", False)
        tools = kwargs.get("tools", None)
        
        # Prepare metadata for logging
        log_metadata = {
            "component": self.component,
            "task_id": task_id,
            "has_tools": tools is not None,
            "thinking_mode": thinking_mode
        }
        
        # Use model's max output tokens if not specified
        if "max_tokens" not in kwargs:
            # Use model's full capacity by default
            kwargs["max_tokens"] = self.model_info.max_output_tokens
        
        # Ensure we don't exceed model's max output tokens
        requested_max_tokens = kwargs.get("max_tokens")
        safe_max_tokens = min(requested_max_tokens, self.model_info.max_output_tokens)
        
        # Log if we're capping the tokens
        if requested_max_tokens > self.model_info.max_output_tokens:
            print(f"[LLM] Capping max_tokens from {requested_max_tokens} to {self.model_info.max_output_tokens} for {self.model}")
        
        try:
            if self.provider == "openai":
                # Build request parameters
                request_params = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": kwargs.get("temperature", 0.2),
                    "max_tokens": safe_max_tokens
                }
                
                # Add tools if provided
                if tools:
                    request_params["tools"] = tools
                    request_params["tool_choice"] = kwargs.get("tool_choice", "auto")
                
                response = self.openai_client.chat.completions.create(**request_params)
                
                # Extract token usage
                input_tokens = response.usage.prompt_tokens
                output_tokens = response.usage.completion_tokens
                
                # Track usage
                self._track_usage(input_tokens, output_tokens, thinking_mode, task_id)
                
                # Return response with tool calls if present
                choice = response.choices[0]
                result = None
                if hasattr(choice.message, 'tool_calls') and choice.message.tool_calls:
                    result = choice.message  # Return the message object with tool_calls
                else:
                    result = choice.message.content.strip() if choice.message.content else ""
                
                # Log the interaction
                self.logger.log_interaction(
                    component=self.component or "unknown",
                    model=self.model,
                    messages=messages,
                    response=result,
                    kwargs=kwargs,
                    metadata=log_metadata
                )
                
                return result
            
            elif self.provider == "google":
                # Check if tools are provided
                if tools:
                    # Handle tool calling for Gemini
                    return self._gemini_chat_with_tools(messages, tools, generation_config={
                        "temperature": kwargs.get("temperature", 0.2),
                        "max_output_tokens": safe_max_tokens,
                    }, log_metadata=log_metadata, task_id=task_id, thinking_mode=thinking_mode)
                else:
                    # Regular text generation without tools
                    # Convert OpenAI-style messages to Gemini format
                    prompt = self._convert_to_gemini_prompt(messages)
                    
                    generation_config = {
                        "temperature": kwargs.get("temperature", 0.2),
                        "max_output_tokens": safe_max_tokens,
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
                    
                    # Log the interaction
                    self.logger.log_interaction(
                        component=self.component or "unknown",
                        model=self.model,
                        messages=messages,
                        response=content,
                        kwargs=kwargs,
                        metadata=log_metadata
                    )
                    
                    return content
            
            elif self.provider == "anthropic":
                # Convert messages to Anthropic format
                system_message = None
                anthropic_messages = []
                
                for msg in messages:
                    if msg["role"] == "system":
                        system_message = msg["content"]
                    elif msg["role"] == "tool":
                        # Handle tool responses - they must be part of a user message
                        # with a tool_result content block
                        anthropic_messages.append({
                            "role": "user",
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": msg["tool_call_id"],
                                    "content": msg["content"]
                                }
                            ]
                        })
                    else:
                        # Handle regular messages and tool calls
                        if msg.get("tool_calls"):
                            # Convert tool calls to content blocks
                            content_blocks = []
                            # Add text content if present
                            if msg.get("content"):
                                content_blocks.append({
                                    "type": "text",
                                    "text": msg["content"]
                                })
                            # Add tool use blocks
                            for tc in msg["tool_calls"]:
                                content_blocks.append({
                                    "type": "tool_use",
                                    "id": tc.get("id", ""),
                                    "name": tc["function"]["name"],
                                    "input": json.loads(tc["function"]["arguments"])
                                })
                            anthropic_messages.append({
                                "role": msg["role"],
                                "content": content_blocks
                            })
                        else:
                            anthropic_messages.append({
                                "role": msg["role"],
                                "content": msg["content"]
                            })
                
                # Build request parameters
                request_params = {
                    "model": self.model,
                    "messages": anthropic_messages,
                    "temperature": kwargs.get("temperature", 0.2),
                    "max_tokens": safe_max_tokens
                }
                
                if system_message:
                    request_params["system"] = system_message
                
                # Add tools if provided
                if tools:
                    # Convert OpenAI tool format to Anthropic format
                    anthropic_tools = []
                    for tool in tools:
                        anthropic_tools.append({
                            "name": tool["name"],
                            "description": tool["description"],
                            "input_schema": tool["parameters"]
                        })
                    request_params["tools"] = anthropic_tools
                
                # Call Anthropic API
                response = self.anthropic_client.messages.create(**request_params)
                
                # Extract usage info
                input_tokens = response.usage.input_tokens
                output_tokens = response.usage.output_tokens
                
                # Track usage
                self._track_usage(input_tokens, output_tokens, thinking_mode, task_id)
                
                # Check for tool use in response
                if tools and response.content:
                    for content in response.content:
                        if content.type == "tool_use":
                            # Return a response object that mimics OpenAI format
                            class AnthropicToolResponse:
                                def __init__(self, response):
                                    self.content = response.content[0].text if any(c.type == "text" for c in response.content) else ""
                                    self.tool_calls = []
                                    for c in response.content:
                                        if c.type == "tool_use":
                                            class ToolCall:
                                                def __init__(self, id, name, arguments):
                                                    self.id = id
                                                    self.function = type('obj', (object,), {
                                                        'name': name,
                                                        'arguments': json.dumps(arguments)
                                                    })
                                            self.tool_calls.append(ToolCall(c.id, c.name, c.input))
                            
                            tool_response = AnthropicToolResponse(response)
                            
                            # Log the interaction with tool calls
                            self.logger.log_interaction(
                                component=self.component or "unknown",
                                model=self.model,
                                messages=messages,
                                response=tool_response,
                                kwargs=kwargs,
                                metadata=log_metadata
                            )
                            
                            return tool_response
                
                # No tool calls, return text
                result = response.content[0].text
                
                # Log the interaction
                self.logger.log_interaction(
                    component=self.component or "unknown",
                    model=self.model,
                    messages=messages,
                    response=result,
                    kwargs=kwargs,
                    metadata=log_metadata
                )
                
                return result
            
            else:
                raise ValueError(f"Provider {self.provider} not implemented in this block")
                
        except Exception as e:
            # Log the error
            self.logger.log_interaction(
                component=self.component or "unknown",
                model=self.model,
                messages=messages,
                response=None,
                kwargs=kwargs,
                error=str(e),
                metadata=log_metadata
            )
            
            # Re-raise the exception
            raise
    
    def _convert_to_gemini_prompt(self, messages: List[Dict[str, str]]) -> str:
        """Convert OpenAI-style messages to a single prompt for Gemini"""
        prompt_parts = []
        
        for msg in messages:
            role = msg["role"]
            content = msg.get("content", "")
            
            if role == "system":
                prompt_parts.append(f"Instructions: {content}")
            elif role == "user":
                prompt_parts.append(f"User: {content}")
            elif role == "assistant":
                # Handle assistant messages that may have tool calls
                if msg.get("tool_calls"):
                    # Format tool calls in the content
                    tool_info = []
                    for tc in msg["tool_calls"]:
                        tool_info.append(f"Using tool: {tc.get('type', 'function')}")
                    if content:
                        prompt_parts.append(f"Assistant: {content} [{', '.join(tool_info)}]")
                    else:
                        prompt_parts.append(f"Assistant: [{', '.join(tool_info)}]")
                else:
                    prompt_parts.append(f"Assistant: {content}")
            elif role == "tool":
                # Handle tool response messages
                tool_id = msg.get("tool_call_id", "unknown")
                prompt_parts.append(f"Tool Result ({tool_id}): {content}")
        
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
    
    def _gemini_chat_with_tools(self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]], 
                                generation_config: Dict[str, Any], log_metadata: Dict[str, Any],
                                task_id: Optional[str], thinking_mode: bool) -> Any:
        """Handle Gemini chat completion with tool calling support."""
        # Convert OpenAI-style tools to Gemini function declarations
        function_declarations = []
        for tool in tools:
            # Convert OpenAI tool format to Gemini format
            # Gemini expects a specific schema format
            parameters = tool.get("parameters", {})
            
            # Convert OpenAI schema to Gemini schema
            gemini_schema = self._convert_openai_to_gemini_schema(parameters)
            
            func_decl = genai.protos.FunctionDeclaration(
                name=tool["name"],
                description=tool["description"],
                parameters=gemini_schema
            )
            function_declarations.append(func_decl)
        
        # Create Gemini tools
        gemini_tools = [genai.protos.Tool(function_declarations=function_declarations)]
        
        # Convert messages to Gemini format
        prompt = self._convert_to_gemini_prompt(messages)
        
        # Generate with tools
        response = self.gemini_model.generate_content(
            prompt,
            generation_config=generation_config,
            tools=gemini_tools
        )
        
        # Handle response
        if not response.candidates:
            raise RuntimeError("No candidates in Gemini response")
        
        candidate = response.candidates[0]
        
        # Check if there are function calls
        if candidate.content.parts:
            for part in candidate.content.parts:
                if hasattr(part, 'function_call') and part.function_call:
                    # Return a response object that mimics OpenAI format
                    class GeminiToolResponse:
                        def __init__(self, candidate):
                            self.content = ""
                            self.tool_calls = []
                            
                            for part in candidate.content.parts:
                                if hasattr(part, 'text') and part.text:
                                    self.content = part.text
                                elif hasattr(part, 'function_call') and part.function_call:
                                    class ToolCall:
                                        def __init__(self, function_call):
                                            import uuid
                                            self.id = str(uuid.uuid4())[:8]  # Generate a short ID
                                            self.function = type('obj', (object,), {
                                                'name': function_call.name,
                                                'arguments': json.dumps(dict(function_call.args))
                                            })
                                    self.tool_calls.append(ToolCall(part.function_call))
                    
                    tool_response = GeminiToolResponse(candidate)
                    
                    # Log the interaction with tool calls
                    self.logger.log_interaction(
                        component=self.component or "unknown",
                        model=self.model,
                        messages=messages,
                        response=tool_response,
                        kwargs={"tools": tools},
                        metadata=log_metadata
                    )
                    
                    return tool_response
        
        # No function calls, return text content
        content = response.text.strip() if hasattr(response, 'text') else candidate.content.parts[0].text.strip()
        
        # Extract token usage
        if hasattr(response, 'usage_metadata'):
            input_tokens = response.usage_metadata.prompt_token_count
            output_tokens = response.usage_metadata.candidates_token_count
        else:
            input_tokens = self._estimate_tokens(prompt)
            output_tokens = self._estimate_tokens(content)
        
        # Track usage
        self._track_usage(input_tokens, output_tokens, thinking_mode, task_id)
        
        # Log the interaction
        self.logger.log_interaction(
            component=self.component or "unknown",
            model=self.model,
            messages=messages,
            response=content,
            kwargs={"tools": tools},
            metadata=log_metadata
        )
        
        return content
    
    def _convert_openai_to_gemini_schema(self, openai_schema: Dict[str, Any]) -> genai.protos.Schema:
        """Convert OpenAI function schema to Gemini Schema format."""
        # Map OpenAI types to Gemini types
        type_mapping = {
            "string": genai.protos.Type.STRING,
            "number": genai.protos.Type.NUMBER,
            "integer": genai.protos.Type.NUMBER,
            "boolean": genai.protos.Type.BOOLEAN,
            "array": genai.protos.Type.ARRAY,
            "object": genai.protos.Type.OBJECT
        }
        
        def convert_property(prop_schema: Dict[str, Any]) -> genai.protos.Schema:
            """Convert a single property schema."""
            prop_type = prop_schema.get("type", "string")
            
            schema_dict = {
                "type": type_mapping.get(prop_type, genai.protos.Type.STRING)
            }
            
            if "description" in prop_schema:
                schema_dict["description"] = prop_schema["description"]
            
            if prop_type == "array" and "items" in prop_schema:
                schema_dict["items"] = convert_property(prop_schema["items"])
            elif prop_type == "object" and "properties" in prop_schema:
                properties = {}
                for key, value in prop_schema["properties"].items():
                    properties[key] = convert_property(value)
                schema_dict["properties"] = properties
                
                if "required" in prop_schema:
                    schema_dict["required"] = prop_schema["required"]
            
            if "enum" in prop_schema:
                schema_dict["enum"] = prop_schema["enum"]
            
            return genai.protos.Schema(**schema_dict)
        
        # Handle root schema
        if openai_schema.get("type") == "object" and "properties" in openai_schema:
            properties = {}
            for key, value in openai_schema["properties"].items():
                properties[key] = convert_property(value)
            
            schema_dict = {
                "type": genai.protos.Type.OBJECT,
                "properties": properties
            }
            
            if "required" in openai_schema:
                schema_dict["required"] = openai_schema["required"]
            
            return genai.protos.Schema(**schema_dict)
        else:
            # Simple schema
            return convert_property(openai_schema)
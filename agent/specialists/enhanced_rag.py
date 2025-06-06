"""
Enhanced RAG Specialist - Provides intelligent context retrieval and synthesis.

This RAG agent can:
- Perform semantic search with LLM-based query understanding
- Synthesize search results into coherent context
- Analyze codebase patterns and architecture
- Build task-specific context for other agents
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import json
from pathlib import Path
from pydantic import BaseModel, Field, ValidationError

from agent.core.base_agent import BaseAgent
from agent.communication.protocol import AgentMessage, MessageType
from agent.communication.broker import MessageBroker


# Pydantic models for structured outputs
class QueryUnderstanding(BaseModel):
    intent: str = Field(description="Brief description of what user wants")
    enhanced_query: str = Field(description="Improved search query")
    file_patterns: List[str] = Field(default_factory=list, description="File patterns to search")
    related_concepts: List[str] = Field(default_factory=list, description="Related concepts to search for")


class ArchitectureAnalysis(BaseModel):
    style: str = Field(description="Architecture style (e.g., MVC, layered, microservices)")
    key_components: List[str] = Field(default_factory=list)
    relationships: List[str] = Field(default_factory=list)


class CodebaseAnalysis(BaseModel):
    summary: str = Field(description="Brief summary of findings")
    patterns: List[str] = Field(default_factory=list)
    architecture: ArchitectureAnalysis
    conventions: Dict[str, str] = Field(default_factory=dict)
    integration_points: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class TaskContext(BaseModel):
    relevant_files: List[str] = Field(default_factory=list)
    patterns: List[str] = Field(default_factory=list)
    imports: List[str] = Field(default_factory=list)
    approach: str = Field(description="Implementation approach")
    testing: str = Field(description="Testing considerations")
    hints: List[str] = Field(default_factory=list)


class EnhancedRAGSpecialist(BaseAgent):
    """
    Enhanced RAG specialist with LLM-based synthesis and analysis.
    """
    
    SYNTHESIS_PROMPT = """You are a code analysis expert. Your role is to:
1. Understand search queries and their intent
2. Synthesize search results into actionable context
3. Identify patterns and architectural decisions
4. Provide relevant context for planning and implementation

IMPORTANT: Always respond with valid JSON. Here are examples of expected formats:

Example 1 - Query Understanding:
```json
{
    "intent": "Find authentication implementations",
    "enhanced_query": "auth login user session token",
    "file_patterns": ["*auth*", "*login*", "*session*"],
    "related_concepts": ["authentication", "authorization", "session management"]
}
```

Example 2 - Codebase Analysis:
```json
{
    "summary": "Multi-agent system with orchestration pattern",
    "patterns": ["delegation", "message-driven", "LLM-based decisions"],
    "architecture": {
        "style": "orchestrated multi-agent",
        "key_components": ["Manager", "Planner", "RAG", "Executor"],
        "relationships": ["Manager -> Planner", "Manager -> RAG", "Manager -> Executor"]
    },
    "conventions": {
        "naming": "CamelCase for classes, snake_case for functions",
        "structure": "agent-based modules with clear separation",
        "testing": "pytest with mocked agent communications"
    },
    "integration_points": ["MessageBroker", "BaseAgent class"],
    "recommendations": ["Use existing broker for new agents", "Follow BaseAgent pattern"]
}
```"""
    
    def __init__(self, model: str = "gemini-2.5-flash-preview-05-20"):  # Use cost-effective Gemini 2.5 Flash
        super().__init__(model=model, component="rag_specialist")
        
        # Enhanced state tracking
        self.search_history: List[Dict[str, Any]] = []
        self.codebase_patterns: Dict[str, Any] = {}
        self.context_cache: Dict[str, Dict[str, Any]] = {}
        
        # Register with message broker
        self.broker = MessageBroker()
        self.broker.register_agent("rag_specialist", self.handle_request)
    
    def handle_request(self, message: AgentMessage) -> Dict[str, Any]:
        """Handle incoming requests for context and search services."""
        try:
            payload = message.payload
            action = payload.get("action", "unknown")
            
            if action == "hybrid_search":
                return self._handle_search_request(payload)
            elif action == "analyze_codebase":
                return self._handle_codebase_analysis(payload)
            elif action == "build_context":
                return self._handle_context_building(payload)
            elif action == "get_status":
                return self._get_status()
            else:
                return {
                    "status": "error",
                    "message": f"Unknown action: {action}",
                    "available_actions": ["hybrid_search", "analyze_codebase", "build_context", "get_status"]
                }
                
        except Exception as e:
            import traceback
            return {
                "status": "error",
                "message": f"Error processing request: {str(e)}",
                "traceback": traceback.format_exc()
            }
    
    def _handle_search_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced search with query understanding and result synthesis."""
        query = payload.get("query", "")
        max_results = payload.get("max_results", 5)
        
        # Use LLM to understand query intent
        query_understanding = self._understand_query(query)
        
        # Enhance query based on understanding
        enhanced_query = query_understanding.get("enhanced_query", query)
        file_hints = query_understanding.get("file_patterns", [])
        
        # Execute hybrid search
        search_results = self._execute_search(enhanced_query, file_hints, max_results * 2)  # Get more for filtering
        
        if not search_results:
            return {
                "status": "error",
                "message": "Search failed",
                "query": query
            }
        
        # Use LLM to synthesize and rank results
        synthesized_results = self._synthesize_results(query, search_results, max_results)
        
        # Track search
        self.search_history.append({
            "query": query,
            "enhanced_query": enhanced_query,
            "timestamp": datetime.now(),
            "results_count": len(synthesized_results)
        })
        
        return {
            "status": "success",
            "query": query,
            "results": synthesized_results,
            "total_found": len(search_results),
            "query_understanding": query_understanding,
            "total_searches": len(self.search_history)
        }
    
    def _handle_codebase_analysis(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Comprehensive codebase analysis for planning."""
        query = payload.get("query", "")
        analysis_type = payload.get("analysis_type", "general")
        
        # First, do a broad search
        search_results = self._execute_search(query, [], 20)  # Get more results for analysis
        
        if not search_results:
            return {
                "status": "error",
                "message": "No relevant code found",
                "query": query
            }
        
        # Analyze patterns and architecture
        analysis = self._analyze_codebase_patterns(query, search_results, analysis_type)
        
        # Cache the analysis
        cache_key = f"{query}:{analysis_type}"
        self.context_cache[cache_key] = analysis
        
        return {
            "status": "success",
            "query": query,
            "analysis": analysis,
            "results": search_results[:10],  # Include top results
            "patterns": analysis.get("patterns", []),
            "summary": analysis.get("summary", ""),
            "recommendations": analysis.get("recommendations", [])
        }
    
    def _handle_context_building(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Build specific context for a task."""
        task_description = payload.get("task_description", "")
        context_type = payload.get("context_type", "execution")
        existing_context = payload.get("existing_context", {})
        
        # Search for relevant code
        search_results = self._execute_search(task_description, [], 10)
        
        # Build task-specific context
        context = self._build_task_context(task_description, search_results, context_type, existing_context)
        
        return {
            "status": "success",
            "task_description": task_description,
            "context": context,
            "relevant_files": context.get("relevant_files", []),
            "key_patterns": context.get("patterns", []),
            "implementation_hints": context.get("hints", [])
        }
    
    def _understand_query(self, query: str) -> Dict[str, Any]:
        """Use LLM to understand search query intent."""
        understanding_prompt = f"""Analyze this code search query and provide search guidance.

Query: "{query}"

Provide:
1. What the user is looking for (intent)
2. Enhanced search query with better keywords
3. Likely file patterns (e.g., "*.py", "*test*", "*config*")
4. Related concepts to search for

Return a JSON object like this example:
```json
{{
    "intent": "Find authentication implementations",
    "enhanced_query": "auth login user session token security",
    "file_patterns": ["*auth*", "*login*", "*user*", "*session*"],
    "related_concepts": ["authentication", "authorization", "JWT", "sessions", "security"]
}}
```

Your JSON response:"""

        try:
            response = self.chat_completion([
                {"role": "system", "content": "You are a code search expert."},
                {"role": "user", "content": understanding_prompt}
            ], temperature=0.3, max_tokens=500)
            
            return self._parse_json_response(response, expected_model=QueryUnderstanding)
        except Exception as e:
            print(f"[RAG] Error understanding query: {e}")
            return {
                "intent": "search for code",
                "enhanced_query": query,
                "file_patterns": [],
                "related_concepts": []
            }
    
    def _execute_search(self, query: str, file_hints: List[str], max_results: int) -> List[Dict[str, Any]]:
        """Execute the actual hybrid search tool."""
        try:
            result = self.execute_tool("hybrid_search", {
                "query": query,
                "file_hints": file_hints,
                "max_results": max_results
            })
            
            if result.get("exit_code") == 0:
                stdout = result.get("stdout", "{}")
                # Handle double-encoded JSON
                if isinstance(stdout, str) and stdout.startswith('{"exit_code"'):
                    # First decode to get the inner result
                    inner_result = json.loads(stdout)
                    if inner_result.get("exit_code") == 0:
                        search_data = json.loads(inner_result.get("stdout", "{}"))
                    else:
                        print(f"[RAG] Inner tool failed: {inner_result.get('stderr', 'Unknown error')}")
                        return []
                else:
                    search_data = json.loads(stdout)
                raw_results = search_data.get("results", [])
                
                # Convert results to expected format
                formatted_results = []
                for res in raw_results:
                    formatted_results.append({
                        "file": res.get("file_path", ""),
                        "file_path": res.get("file_path", ""),
                        "start_line": res.get("start_line", 0),
                        "end_line": res.get("end_line", 0),
                        "content": res.get("text", ""),
                        "score": res.get("score", 0.0),
                        "chunk_id": res.get("chunk_id", "")
                    })
                return formatted_results
            else:
                print(f"[RAG] Search failed: {result.get('stderr', 'Unknown error')}")
                return []
                
        except Exception as e:
            print(f"[RAG] Error executing search: {e}")
            return []
    
    def _synthesize_results(self, original_query: str, results: List[Dict[str, Any]], max_results: int) -> List[Dict[str, Any]]:
        """Use LLM to synthesize and rank search results."""
        if not results:
            return []
        
        # Prepare results for LLM
        results_text = ""
        for i, result in enumerate(results[:max_results * 2]):  # Analyze more than we'll return
            results_text += f"\nResult {i+1}:\n"
            results_text += f"File: {result.get('file', 'Unknown')}\n"
            results_text += f"Score: {result.get('score', 0)}\n"
            results_text += f"Content: {result.get('content', '')[:500]}...\n"
        
        synthesis_prompt = f"""Analyze these search results for the query: "{original_query}"

{results_text}

Select and rank the {max_results} most relevant results. For each:
1. Explain why it's relevant
2. Extract key information
3. Note any patterns or relationships

Return a JSON array of the top {max_results} results with enhanced information:
[
    {{
        "rank": 1,
        "file": "path/to/file",
        "relevance_reason": "why this is relevant",
        "key_info": "important extracted information",
        "patterns": ["pattern1", "pattern2"],
        "original_score": 0.95
    }}
]"""

        try:
            response = self.chat_completion([
                {"role": "system", "content": self.SYNTHESIS_PROMPT},
                {"role": "user", "content": synthesis_prompt}
            ], temperature=0.3)  # Use model's default max_tokens from registry
            
            synthesized = self._parse_json_response(response)
            
            # Merge synthesized info with original results
            enhanced_results = []
            for item in synthesized:
                # Find original result
                for result in results:
                    if result.get("file") == item.get("file"):
                        enhanced_result = result.copy()
                        enhanced_result.update({
                            "relevance_reason": item.get("relevance_reason", ""),
                            "key_info": item.get("key_info", ""),
                            "patterns": item.get("patterns", []),
                            "rank": item.get("rank", 999)
                        })
                        enhanced_results.append(enhanced_result)
                        break
            
            return enhanced_results[:max_results]
            
        except Exception as e:
            print(f"[RAG] Error synthesizing results: {e}")
            return results[:max_results]  # Fallback to original results
    
    def _analyze_codebase_patterns(self, query: str, results: List[Dict[str, Any]], analysis_type: str) -> Dict[str, Any]:
        """Analyze codebase patterns and architecture."""
        # Prepare code samples for analysis
        code_samples = ""
        file_list = []
        for result in results[:15]:  # Analyze top 15 results
            file_path = result.get("file", "Unknown")
            file_list.append(file_path)
            code_samples += f"\n\n--- {file_path} ---\n"
            # Include full content - let model handle truncation based on its limits
            code_samples += result.get("content", "")
        
        analysis_prompt = f"""Analyze this codebase for: "{query}"

Analysis type: {analysis_type}

Files found:
{json.dumps(file_list, indent=2)}

Code samples:
{code_samples}

Provide a comprehensive analysis:
1. Overall architecture and patterns
2. Key components and their relationships
3. Coding conventions and style
4. Integration points for new features
5. Potential challenges or considerations

Return a JSON object like this example:
```json
{{
    "summary": "Multi-agent system using orchestration pattern with specialized agents",
    "patterns": ["message broker", "base agent inheritance", "LLM integration", "tool system"],
    "architecture": {{
        "style": "orchestrated multi-agent",
        "key_components": ["OrchestratingManager", "EnhancedPlanner", "EnhancedRAG", "ExecutorPool"],
        "relationships": ["Manager -> Planner", "Manager -> RAG", "Manager -> Executor", "Planner -> RAG"]
    }},
    "conventions": {{
        "naming": "CamelCase classes, snake_case methods, descriptive names",
        "structure": "agent modules with base class inheritance",
        "testing": "pytest with mocked agent communications"
    }},
    "integration_points": ["MessageBroker for communication", "BaseAgent for new agents", "Tool registry"],
    "recommendations": ["Use MessageBroker for agent communication", "Inherit from BaseAgent", "Register tools properly"]
}}
```

Your JSON response:"""

        try:
            response = self.chat_completion([
                {"role": "system", "content": self.SYNTHESIS_PROMPT},
                {"role": "user", "content": analysis_prompt}
            ], temperature=0.3)  # Use model's default max_tokens from registry
            
            analysis = self._parse_json_response(response, expected_model=CodebaseAnalysis)
            
            # Store patterns for future use
            self.codebase_patterns.update({
                "last_analysis": datetime.now(),
                "patterns": analysis.get("patterns", []),
                "architecture": analysis.get("architecture", {})
            })
            
            return analysis
            
        except Exception as e:
            print(f"[RAG] Error analyzing codebase: {e}")
            return {
                "summary": "Analysis failed",
                "patterns": [],
                "error": str(e)
            }
    
    def _build_task_context(self, task: str, results: List[Dict[str, Any]], context_type: str, existing: Dict[str, Any]) -> Dict[str, Any]:
        """Build task-specific context."""
        context_prompt = f"""Build implementation context for this task: "{task}"

Context type: {context_type}

Relevant code found:
{json.dumps([{"file": r.get("file"), "preview": r.get("content", "")[:200]} for r in results[:5]], indent=2)}

Existing context:
{json.dumps(existing, indent=2) if existing else "None"}

Provide context for implementation:
1. Relevant files to modify or reference
2. Code patterns to follow
3. Dependencies and imports needed
4. Implementation approach
5. Testing considerations

Return a JSON object like this example:
```json
{
    "relevant_files": ["agent/core/base_agent.py", "agent/communication/broker.py"],
    "patterns": ["inherit from BaseAgent", "use MessageBroker for communication", "implement handle_request"],
    "imports": ["from agent.core.base_agent import BaseAgent", "from agent.communication.broker import MessageBroker"],
    "approach": "Create new agent class inheriting BaseAgent, implement required methods, register with broker",
    "testing": "Mock MessageBroker, test handle_request method, verify message routing",
    "hints": ["Look at existing agents for examples", "Register agent type in factory", "Add to agent registry"]
}
```

Your JSON response:"""

        try:
            response = self.chat_completion([
                {"role": "system", "content": "You are a senior developer providing implementation guidance."},
                {"role": "user", "content": context_prompt}
            ], temperature=0.3)  # Use model's default max_tokens from registry
            
            return self._parse_json_response(response, expected_model=TaskContext)
            
        except Exception as e:
            print(f"[RAG] Error building context: {e}")
            return {
                "relevant_files": [r.get("file") for r in results[:3]],
                "patterns": [],
                "error": str(e)
            }
    
    def _parse_json_response(self, response: str, expected_model: Optional[type] = None, 
                           retry_on_fail: bool = True, max_retries: int = 3) -> Dict[str, Any]:
        """Parse JSON from LLM response with retries and validation."""
        import re
        
        def extract_json(text: str) -> Optional[str]:
            """Extract JSON from various formats."""
            # Look for ```json blocks first
            json_block = re.search(r'```(?:json)?\s*\n(.*?)\n```', text, re.DOTALL)
            if json_block:
                return json_block.group(1).strip()
            
            # Try to extract JSON object or array
            json_match = re.search(r'\{.*\}|\[.*\]', text, re.DOTALL)
            if json_match:
                return json_match.group().strip()
            
            return None
        
        # Try to parse the response
        attempts = 0
        last_error = None
        
        while attempts < max_retries:
            try:
                # Try direct parsing first
                json_str = response if attempts == 0 else extract_json(response)
                if not json_str:
                    json_str = response.strip()
                
                parsed = json.loads(json_str)
                
                # If we have a Pydantic model, validate against it
                if expected_model:
                    validated = expected_model(**parsed)
                    return validated.model_dump()
                
                return parsed
                
            except (json.JSONDecodeError, ValidationError) as e:
                last_error = e
                attempts += 1
                
                if retry_on_fail and attempts < max_retries:
                    print(f"[RAG] JSON parsing failed (attempt {attempts}/{max_retries}): {e}")
                    
                    # Ask for a retry with clearer instructions
                    retry_prompt = f"""Your previous response could not be parsed as valid JSON.
Error: {str(e)}

Please provide your response as valid JSON only. Example format:
```json
{{
    "key": "value",
    "list": ["item1", "item2"],
    "nested": {{"inner": "value"}}
}}
```

Original response to fix:
{response[:500]}...

Respond with ONLY the JSON, no additional text."""
                    
                    # Get a new response
                    retry_response = self.chat_completion([
                        {"role": "system", "content": "You are a JSON formatting assistant. Respond only with valid JSON."},
                        {"role": "user", "content": retry_prompt}
                    ], temperature=0.1, max_tokens=2000)
                    
                    response = retry_response
                else:
                    break
        
        # All attempts failed
        raise ValueError(f"Could not parse JSON after {attempts} attempts. Last error: {last_error}")
    
    def _get_status(self) -> Dict[str, Any]:
        """Get current RAG specialist status."""
        return {
            "status": "active",
            "total_searches": len(self.search_history),
            "cached_contexts": len(self.context_cache),
            "has_patterns": bool(self.codebase_patterns),
            "recent_searches": [
                {
                    "query": search["query"],
                    "timestamp": search["timestamp"].isoformat(),
                    "results_found": search["results_count"]
                }
                for search in self.search_history[-5:]
            ]
        }
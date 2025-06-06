"""
Enhanced Executor Pool - Context-aware code generation with detailed reporting.

This executor can:
- Use RAG context effectively for implementation
- Generate code with proper tool usage
- Provide detailed failure reports for replanning
- Track implementation progress
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import json
import re
from pathlib import Path

from agent.core.base_agent import BaseAgent
from agent.communication.protocol import AgentMessage, MessageType
from agent.communication.broker import MessageBroker


class EnhancedExecutorAgent(BaseAgent):
    """Enhanced executor with context awareness and detailed reporting."""
    
    IMPLEMENTATION_PROMPT = """You are an expert software engineer implementing specific tasks.

Key principles:
1. Use the provided context to understand existing code patterns
2. Follow the project's conventions and style
3. Write clean, maintainable code with proper error handling
4. Use available tools to read files, write diffs, and run tests
5. Report progress and any issues clearly"""
    
    def __init__(self, executor_id: int, model: str = "claude-sonnet-4-20250514"):
        super().__init__(model=model, component="executor")
        self.executor_id = executor_id
        self.execution_history: List[Dict[str, Any]] = []
        self.current_task: Optional[Dict[str, Any]] = None
    
    def handle_request(self, message: AgentMessage) -> Dict[str, Any]:
        """Handle incoming requests - required by BaseAgent."""
        return {"status": "received", "message": f"Executor {self.executor_id} managed by pool"}
    
    def execute_task(self, task_id: str, task_description: str, context: Dict[str, Any], 
                     acceptance_criteria: List[str] = None) -> Dict[str, Any]:
        """Execute a task with full context awareness."""
        
        self.current_task = {
            "task_id": task_id,
            "description": task_description,
            "context": context,
            "acceptance_criteria": acceptance_criteria or [],
            "start_time": datetime.now()
        }
        
        try:
            # Analyze the task and context
            analysis = self._analyze_task(task_description, context, acceptance_criteria)
            
            # Generate implementation plan
            implementation_plan = self._create_implementation_plan(analysis)
            
            # Execute the implementation
            implementation_result = self._execute_implementation(implementation_plan)
            
            # Validate against acceptance criteria
            validation_result = self._validate_implementation(implementation_result, acceptance_criteria)
            
            # Build detailed result
            result = self._build_execution_result(
                "success" if validation_result["passed"] else "partial",
                analysis,
                implementation_plan,
                implementation_result,
                validation_result
            )
            
            # Track execution
            self.execution_history.append({
                **self.current_task,
                "end_time": datetime.now(),
                "result": result
            })
            
            return result
            
        except Exception as e:
            # Build detailed failure report
            import traceback
            failure_result = self._build_failure_report(e, traceback.format_exc())
            
            self.execution_history.append({
                **self.current_task,
                "end_time": datetime.now(),
                "result": failure_result
            })
            
            return failure_result
    
    def _analyze_task(self, description: str, context: Dict[str, Any], criteria: List[str]) -> Dict[str, Any]:
        """Analyze the task using LLM with context."""
        
        # Build analysis prompt
        analysis_prompt = f"""Analyze this implementation task:

Task: {description}

Context provided:
- Relevant files: {len(context.get('relevant_files', []))}
- Key patterns: {', '.join(context.get('patterns', ['None']))}
- Dependencies: {', '.join(context.get('dependencies', ['None']))}

Acceptance criteria:
{json.dumps(criteria, indent=2) if criteria else 'None specified'}

Provide analysis:
1. What needs to be implemented
2. Which files to modify or create
3. Key challenges or considerations
4. Required tools and operations
5. Success metrics

Return JSON with your analysis."""

        try:
            response = self.chat_completion([
                {"role": "system", "content": self.IMPLEMENTATION_PROMPT},
                {"role": "user", "content": analysis_prompt}
            ], temperature=0.3)  # Use model's default max_tokens from registry
            
            return self._parse_json_response(response)
            
        except Exception as e:
            print(f"[Executor-{self.executor_id}] Error analyzing task: {e}")
            return {
                "summary": "Basic analysis",
                "files_to_modify": [],
                "challenges": ["Analysis failed"],
                "required_tools": ["read_file", "write_diff"],
                "error": str(e)
            }
    
    def _create_implementation_plan(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create step-by-step implementation plan."""
        
        plan_prompt = f"""Based on this task analysis, create a step-by-step implementation plan:

{json.dumps(analysis, indent=2)}

Create specific steps with:
1. Clear action (read file, modify code, create test, etc.)
2. Target file or component
3. Specific changes or operations
4. Tool to use

Return JSON array of steps:
[
    {{
        "step": 1,
        "action": "read existing implementation",
        "target": "path/to/file.py",
        "tool": "read_file",
        "purpose": "understand current structure"
    }}
]"""

        try:
            response = self.chat_completion([
                {"role": "system", "content": "You are planning code implementation steps."},
                {"role": "user", "content": plan_prompt}
            ], temperature=0.3, max_tokens=1500)
            
            steps = self._parse_json_response(response)
            return steps if isinstance(steps, list) else steps.get("steps", [])
            
        except Exception as e:
            print(f"[Executor-{self.executor_id}] Error creating plan: {e}")
            # Fallback plan
            return [{
                "step": 1,
                "action": "implement task",
                "target": "unknown",
                "tool": "write_diff",
                "purpose": "complete task"
            }]
    
    def _execute_implementation(self, plan: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute the implementation plan step by step."""
        
        results = {
            "steps_completed": [],
            "files_modified": [],
            "files_created": [],
            "tests_run": False,
            "errors": []
        }
        
        for step in plan:
            try:
                step_result = self._execute_step(step)
                results["steps_completed"].append({
                    "step": step,
                    "result": step_result
                })
                
                # Track file changes
                if step["tool"] == "write_diff" and step_result.get("success"):
                    if step_result.get("created"):
                        results["files_created"].append(step["target"])
                    else:
                        results["files_modified"].append(step["target"])
                        
                elif step["tool"] == "run_tests" and step_result.get("success"):
                    results["tests_run"] = True
                    
            except Exception as e:
                results["errors"].append({
                    "step": step,
                    "error": str(e)
                })
                
        return results
    
    def _execute_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single implementation step."""
        
        tool_name = step.get("tool", "")
        target = step.get("target", "")
        
        # Build tool-specific prompt
        if tool_name == "read_file":
            # Read file to understand context
            try:
                result = self.execute_tool("read_file", {"file_path": target})
                return {
                    "success": result.get("exit_code") == 0,
                    "content": result.get("stdout", ""),
                    "error": result.get("stderr", "")
                }
            except Exception as e:
                return {"success": False, "error": str(e)}
                
        elif tool_name == "write_diff":
            # Generate and apply code changes
            code_prompt = f"""Based on the implementation plan, generate the code for this step:

Step: {json.dumps(step, indent=2)}

Current task context:
{json.dumps(self.current_task.get('context', {}), indent=2)}

Generate the complete code that should be written to {target}.
If modifying existing code, show the full updated version."""

            try:
                code_response = self.chat_completion([
                    {"role": "system", "content": "Generate clean, working code."},
                    {"role": "user", "content": code_prompt}
                ], temperature=0.2)  # Use model's default max_tokens from registry
                
                # Extract code from response
                code = self._extract_code_from_response(code_response)
                
                # Write the code
                write_result = self.execute_tool("write_diff", {
                    "file_path": target,
                    "new_content": code
                })
                
                return {
                    "success": write_result.get("exit_code") == 0,
                    "created": not Path(target).exists(),
                    "content": code[:500] + "..." if len(code) > 500 else code,
                    "error": write_result.get("stderr", "")
                }
                
            except Exception as e:
                return {"success": False, "error": str(e)}
                
        elif tool_name == "run_tests":
            # Run tests
            try:
                test_result = self.execute_tool("run_tests", {"test_path": target})
                return {
                    "success": test_result.get("exit_code") == 0,
                    "output": test_result.get("stdout", ""),
                    "error": test_result.get("stderr", "")
                }
            except Exception as e:
                return {"success": False, "error": str(e)}
                
        else:
            # Generic tool execution
            try:
                result = self.execute_tool(tool_name, step.get("args", {}))
                return {
                    "success": result.get("exit_code") == 0,
                    "output": result.get("stdout", ""),
                    "error": result.get("stderr", "")
                }
            except Exception as e:
                return {"success": False, "error": str(e)}
    
    def _validate_implementation(self, implementation: Dict[str, Any], criteria: List[str]) -> Dict[str, Any]:
        """Validate implementation against acceptance criteria."""
        
        if not criteria:
            # No specific criteria, check basic success
            return {
                "passed": len(implementation.get("errors", [])) == 0,
                "criteria_results": [],
                "summary": "No specific criteria to validate"
            }
        
        validation_prompt = f"""Validate this implementation against acceptance criteria:

Implementation results:
{json.dumps(implementation, indent=2)}

Acceptance criteria:
{json.dumps(criteria, indent=2)}

For each criterion, determine if it was met based on the implementation.

Return JSON:
{{
    "criteria_results": [
        {{
            "criterion": "criterion text",
            "met": true/false,
            "evidence": "why this was or wasn't met"
        }}
    ],
    "overall_passed": true/false,
    "recommendations": ["any recommendations"]
}}"""

        try:
            response = self.chat_completion([
                {"role": "system", "content": "You are validating code implementation."},
                {"role": "user", "content": validation_prompt}
            ], temperature=0.3, max_tokens=1500)
            
            validation = self._parse_json_response(response)
            
            return {
                "passed": validation.get("overall_passed", False),
                "criteria_results": validation.get("criteria_results", []),
                "summary": f"{sum(1 for r in validation.get('criteria_results', []) if r.get('met'))} of {len(criteria)} criteria met",
                "recommendations": validation.get("recommendations", [])
            }
            
        except Exception as e:
            return {
                "passed": False,
                "criteria_results": [],
                "summary": f"Validation failed: {str(e)}",
                "error": str(e)
            }
    
    def _build_execution_result(self, status: str, analysis: Dict[str, Any], 
                                plan: List[Dict[str, Any]], implementation: Dict[str, Any],
                                validation: Dict[str, Any]) -> Dict[str, Any]:
        """Build comprehensive execution result."""
        
        return {
            "status": status,
            "task_id": self.current_task["task_id"],
            "summary": self._generate_summary(status, implementation, validation),
            "analysis": analysis,
            "plan": plan,
            "implementation": {
                "steps_completed": len(implementation.get("steps_completed", [])),
                "files_modified": implementation.get("files_modified", []),
                "files_created": implementation.get("files_created", []),
                "tests_run": implementation.get("tests_run", False),
                "errors": implementation.get("errors", [])
            },
            "validation": validation,
            "duration_seconds": (datetime.now() - self.current_task["start_time"]).total_seconds()
        }
    
    def _build_failure_report(self, error: Exception, traceback: str) -> Dict[str, Any]:
        """Build detailed failure report for replanning."""
        
        return {
            "status": "failed",
            "task_id": self.current_task["task_id"],
            "error": str(error),
            "error_type": type(error).__name__,
            "traceback": traceback,
            "summary": f"Task failed: {str(error)[:100]}",
            "context_used": {
                "had_relevant_files": bool(self.current_task["context"].get("relevant_files")),
                "had_patterns": bool(self.current_task["context"].get("patterns")),
                "had_dependencies": bool(self.current_task["context"].get("dependencies"))
            },
            "recommendations": [
                "Check if required files exist",
                "Verify tool permissions",
                "Consider breaking task into smaller steps"
            ],
            "duration_seconds": (datetime.now() - self.current_task["start_time"]).total_seconds()
        }
    
    def _extract_code_from_response(self, response: str) -> str:
        """Extract code from LLM response."""
        # Look for code blocks
        code_blocks = re.findall(r'```(?:python)?\n(.*?)\n```', response, re.DOTALL)
        if code_blocks:
            return code_blocks[0]
        
        # If no code blocks, assume entire response is code
        return response.strip()
    
    def _parse_json_response(self, response: str) -> Any:
        """Parse JSON from LLM response."""
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Try to extract JSON
            json_match = re.search(r'\{.*\}|\[.*\]', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                raise ValueError("Could not parse JSON from response")
    
    def _generate_summary(self, status: str, implementation: Dict[str, Any], validation: Dict[str, Any]) -> str:
        """Generate execution summary."""
        if status == "success":
            return f"Successfully completed task. Modified {len(implementation.get('files_modified', []))} files, created {len(implementation.get('files_created', []))} files. {validation.get('summary', '')}"
        elif status == "partial":
            return f"Partially completed task. {validation.get('summary', '')}. See validation results for details."
        else:
            return f"Task execution failed. Completed {len(implementation.get('steps_completed', []))} steps before failure."


class EnhancedExecutorPool:
    """
    Enhanced pool of executor agents with better coordination and reporting.
    """
    
    def __init__(self, pool_size: int = 3, model: str = "claude-sonnet-4-20250514"):
        self.pool_size = pool_size
        self.executors: List[EnhancedExecutorAgent] = []
        self.model = model
        
        # Create executor agents
        for i in range(pool_size):
            self.executors.append(EnhancedExecutorAgent(executor_id=i, model=model))
        
        # Track execution state
        self.execution_queue: List[Dict[str, Any]] = []
        self.execution_history: List[Dict[str, Any]] = []
        self.active_executions: Dict[str, Dict[str, Any]] = {}
        
        # Register with message broker
        self.broker = MessageBroker()
        self.broker.register_agent("executor", self.handle_request)
    
    def handle_request(self, message: AgentMessage) -> Dict[str, Any]:
        """Handle incoming execution requests."""
        try:
            payload = message.payload
            action = payload.get("action", "unknown")
            
            if action == "execute_task":
                return self._handle_execution_request(payload)
            elif action == "get_status":
                return self._get_status()
            elif action == "get_task_result":
                return self._get_task_result(payload.get("task_id"))
            else:
                return {
                    "status": "error",
                    "message": f"Unknown action: {action}",
                    "available_actions": ["execute_task", "get_status", "get_task_result"]
                }
                
        except Exception as e:
            import traceback
            return {
                "status": "error",
                "message": f"Error processing request: {str(e)}",
                "traceback": traceback.format_exc()
            }
    
    def _handle_execution_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle task execution request with enhanced context."""
        task_id = payload.get("task_id", f"T-{datetime.now().strftime('%Y%m%d%H%M%S')}")
        task_description = payload.get("task_description", "")
        context = payload.get("context", {})
        acceptance_criteria = payload.get("acceptance_criteria", [])
        
        # Find available executor
        executor = self._get_available_executor()
        
        # Track active execution
        self.active_executions[task_id] = {
            "task_id": task_id,
            "executor_id": executor.executor_id,
            "start_time": datetime.now(),
            "status": "executing"
        }
        
        # Execute the task
        result = executor.execute_task(task_id, task_description, context, acceptance_criteria)
        
        # Update tracking
        self.active_executions.pop(task_id, None)
        self.execution_history.append({
            "task_id": task_id,
            "description": task_description,
            "timestamp": datetime.now(),
            "executor_id": executor.executor_id,
            "result": result
        })
        
        # Report progress if task partially succeeded
        if result["status"] == "partial":
            # Send progress report to manager
            self._report_progress(task_id, result)
        elif result["status"] == "failed":
            # Send failure report for potential replanning
            self._report_failure(task_id, result)
        
        return result
    
    def _get_available_executor(self) -> EnhancedExecutorAgent:
        """Get the least busy executor."""
        # Simple strategy: rotate through executors
        executor_loads = {}
        for executor in self.executors:
            active_count = sum(1 for exec_info in self.active_executions.values() 
                             if exec_info["executor_id"] == executor.executor_id)
            executor_loads[executor.executor_id] = active_count
        
        # Get executor with minimum load
        min_load_id = min(executor_loads, key=executor_loads.get)
        return self.executors[min_load_id]
    
    def _report_progress(self, task_id: str, result: Dict[str, Any]) -> None:
        """Report partial progress to manager."""
        try:
            message = AgentMessage(
                sender="executor",
                recipient="manager",
                message_type=MessageType.REQUEST,
                payload={
                    "action": "report_progress",
                    "task_id": task_id,
                    "progress": {
                        "status": "partial",
                        "completed_steps": result["implementation"]["steps_completed"],
                        "validation_summary": result["validation"]["summary"]
                    }
                }
            )
            self.broker.send_request(message, timeout=5.0)
        except Exception as e:
            print(f"[ExecutorPool] Failed to report progress: {e}")
    
    def _report_failure(self, task_id: str, result: Dict[str, Any]) -> None:
        """Report failure to manager for replanning."""
        try:
            message = AgentMessage(
                sender="executor",
                recipient="manager",
                message_type=MessageType.REQUEST,
                payload={
                    "action": "report_failure",
                    "task_id": task_id,
                    "error_info": {
                        "error": result.get("error", "Unknown error"),
                        "error_type": result.get("error_type", "Unknown"),
                        "summary": result.get("summary", ""),
                        "recommendations": result.get("recommendations", [])
                    }
                }
            )
            self.broker.send_request(message, timeout=5.0)
        except Exception as e:
            print(f"[ExecutorPool] Failed to report failure: {e}")
    
    def _get_task_result(self, task_id: str) -> Dict[str, Any]:
        """Get result for a specific task."""
        for execution in self.execution_history:
            if execution["task_id"] == task_id:
                return {
                    "status": "found",
                    "result": execution["result"]
                }
        
        if task_id in self.active_executions:
            return {
                "status": "executing",
                "executor_id": self.active_executions[task_id]["executor_id"]
            }
        
        return {
            "status": "not_found",
            "message": f"Task {task_id} not found"
        }
    
    def _get_status(self) -> Dict[str, Any]:
        """Get comprehensive pool status."""
        return {
            "status": "active",
            "pool_size": self.pool_size,
            "active_executions": len(self.active_executions),
            "total_completed": len(self.execution_history),
            "executors": [
                {
                    "id": executor.executor_id,
                    "tasks_completed": len(executor.execution_history),
                    "current_task": executor.current_task["task_id"] if executor.current_task else None
                }
                for executor in self.executors
            ],
            "recent_executions": [
                {
                    "task_id": exec_info["task_id"],
                    "status": exec_info["result"]["status"],
                    "summary": exec_info["result"].get("summary", "")[:100]
                }
                for exec_info in self.execution_history[-5:]
            ]
        }
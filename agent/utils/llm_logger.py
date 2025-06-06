"""
LLM interaction logger - saves each input/output pair as a separate file for debugging.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import hashlib


class LLMLogger:
    """
    Logger for LLM interactions. Saves each request/response pair as a separate JSON file.
    """
    
    def __init__(self, log_dir: str = "llm_logs"):
        """
        Initialize the logger.
        
        Args:
            log_dir: Directory to save log files
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Create subdirectories for each component
        self.component_dirs = {}
    
    def _get_component_dir(self, component: str) -> Path:
        """Get or create directory for a specific component."""
        if component not in self.component_dirs:
            component_dir = self.log_dir / component
            component_dir.mkdir(exist_ok=True)
            self.component_dirs[component] = component_dir
        return self.component_dirs[component]
    
    def log_interaction(
        self, 
        component: str,
        model: str,
        messages: List[Dict[str, Any]],
        response: Any,
        kwargs: Dict[str, Any],
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Log a single LLM interaction.
        
        Args:
            component: Component name (manager, planner, rag, executor)
            model: Model identifier
            messages: Input messages sent to LLM
            response: Response from LLM (can be string or object)
            kwargs: Additional kwargs passed to LLM
            error: Error message if request failed
            metadata: Additional metadata to log
            
        Returns:
            Path to the log file
        """
        # Generate timestamp-based filename
        timestamp = datetime.now()
        timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S_%f")[:-3]  # Include milliseconds
        
        # Add a short hash of the content for uniqueness
        content_hash = hashlib.md5(json.dumps(messages).encode()).hexdigest()[:6]
        
        # Create filename
        status = "error" if error else "success"
        filename = f"{timestamp_str}_{status}_{content_hash}.json"
        
        # Get component directory
        component_dir = self._get_component_dir(component)
        filepath = component_dir / filename
        
        # Prepare log data
        log_data = {
            "timestamp": timestamp.isoformat(),
            "component": component,
            "model": model,
            "status": status,
            "input": {
                "messages": messages,
                "kwargs": kwargs
            },
            "output": {
                "response": self._serialize_response(response),
                "error": error
            },
            "metadata": metadata or {},
            "stats": {
                "input_message_count": len(messages),
                "input_chars": sum(len(str(msg.get("content", ""))) for msg in messages),
                "output_chars": len(str(response)) if response else 0
            }
        }
        
        # Add tool information if present
        if "tools" in kwargs:
            log_data["input"]["tools_provided"] = [
                {"name": tool.get("name"), "description": tool.get("description", "")[:100] + "..."}
                for tool in kwargs.get("tools", [])
            ]
        
        # Check if response has tool calls
        if hasattr(response, 'tool_calls'):
            log_data["output"]["had_tool_calls"] = True
            log_data["output"]["tool_calls"] = [
                {
                    "id": tc.id if hasattr(tc, 'id') else tc.get('id'),
                    "name": tc.function.name if hasattr(tc, 'function') else tc.get('function', {}).get('name'),
                    "arguments": tc.function.arguments if hasattr(tc, 'function') else tc.get('function', {}).get('arguments')
                }
                for tc in response.tool_calls
            ]
        
        # Write to file
        with open(filepath, 'w') as f:
            json.dump(log_data, f, indent=2, default=str)
        
        return str(filepath)
    
    def _serialize_response(self, response: Any) -> Any:
        """Serialize response object to JSON-compatible format."""
        if response is None:
            return None
        elif isinstance(response, str):
            return response
        elif isinstance(response, dict):
            return response
        elif hasattr(response, 'content'):
            # Handle response objects with content attribute
            return {
                "content": response.content,
                "type": type(response).__name__,
                "has_tool_calls": hasattr(response, 'tool_calls') and response.tool_calls is not None
            }
        else:
            # Fallback to string representation
            return str(response)
    
    def get_recent_logs(self, component: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent log entries for a component.
        
        Args:
            component: Component name
            limit: Maximum number of logs to return
            
        Returns:
            List of log entries (most recent first)
        """
        component_dir = self._get_component_dir(component)
        
        # Get all JSON files in the directory
        log_files = sorted(
            component_dir.glob("*.json"),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )[:limit]
        
        logs = []
        for log_file in log_files:
            try:
                with open(log_file, 'r') as f:
                    log_data = json.load(f)
                    log_data["_filename"] = log_file.name
                    logs.append(log_data)
            except Exception as e:
                print(f"Error reading log file {log_file}: {e}")
        
        return logs
    
    def get_error_logs(self, component: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get recent error logs.
        
        Args:
            component: Component name (or None for all components)
            limit: Maximum number of logs to return
            
        Returns:
            List of error log entries
        """
        if component:
            component_dirs = [self._get_component_dir(component)]
        else:
            # Get all component directories
            component_dirs = [d for d in self.log_dir.iterdir() if d.is_dir()]
        
        error_logs = []
        for component_dir in component_dirs:
            # Get error files
            error_files = sorted(
                component_dir.glob("*_error_*.json"),
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )
            
            for log_file in error_files[:limit]:
                try:
                    with open(log_file, 'r') as f:
                        log_data = json.load(f)
                        log_data["_filename"] = log_file.name
                        log_data["_component"] = component_dir.name
                        error_logs.append(log_data)
                except Exception as e:
                    print(f"Error reading log file {log_file}: {e}")
        
        # Sort by timestamp and limit
        error_logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return error_logs[:limit]
    
    def clear_logs(self, component: Optional[str] = None, older_than_hours: Optional[int] = None):
        """
        Clear log files.
        
        Args:
            component: Component name (or None for all components)
            older_than_hours: Only delete logs older than this many hours (or None for all)
        """
        if component:
            component_dirs = [self._get_component_dir(component)]
        else:
            component_dirs = [d for d in self.log_dir.iterdir() if d.is_dir()]
        
        cutoff_time = None
        if older_than_hours:
            cutoff_time = datetime.now().timestamp() - (older_than_hours * 3600)
        
        deleted_count = 0
        for component_dir in component_dirs:
            for log_file in component_dir.glob("*.json"):
                try:
                    if cutoff_time is None or log_file.stat().st_mtime < cutoff_time:
                        log_file.unlink()
                        deleted_count += 1
                except Exception as e:
                    print(f"Error deleting {log_file}: {e}")
        
        print(f"Deleted {deleted_count} log files")
        return deleted_count
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about logged interactions."""
        stats = {
            "total_logs": 0,
            "by_component": {},
            "errors": 0,
            "with_tool_calls": 0
        }
        
        for component_dir in self.log_dir.iterdir():
            if component_dir.is_dir():
                component_name = component_dir.name
                log_files = list(component_dir.glob("*.json"))
                error_files = list(component_dir.glob("*_error_*.json"))
                
                stats["by_component"][component_name] = {
                    "total": len(log_files),
                    "errors": len(error_files),
                    "success": len(log_files) - len(error_files)
                }
                
                stats["total_logs"] += len(log_files)
                stats["errors"] += len(error_files)
        
        return stats


# Global logger instance
_logger = None

def get_llm_logger() -> LLMLogger:
    """Get the global LLM logger instance."""
    global _logger
    if _logger is None:
        _logger = LLMLogger()
    return _logger
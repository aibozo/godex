#!/usr/bin/env python3
"""Mock hybrid search tool for testing without ChromaDB."""

import sys
import json
from typing import Dict, Any, List


def main():
    if len(sys.argv) != 2:
        err = {"exit_code": 1, "stdout": "", "stderr": "Expected exactly one JSON arg"}
        print(json.dumps(err))
        sys.exit(1)

    try:
        args = json.loads(sys.argv[1])
        query = args.get("query")
        file_hints = args.get("file_hints", [])
        max_results = args.get("max_results", 5)
        
        if not query:
            raise ValueError("Missing 'query'")
        
        result = mock_hybrid_search(query, file_hints, max_results)
        resp = {"exit_code": 0, "stdout": json.dumps(result), "stderr": ""}
        
    except Exception as e:
        resp = {"exit_code": 1, "stdout": "", "stderr": str(e)}

    print(json.dumps(resp))
    sys.exit(resp["exit_code"])


def mock_hybrid_search(query: str, file_hints: List[str], max_results: int) -> Dict[str, Any]:
    """
    Mock hybrid search results for testing.
    """
    # Create mock results based on the query
    mock_results = []
    
    if "calculator" in query.lower():
        mock_results = [
            {
                "file_path": "workspace/calculator_project/src/calculator.py",
                "start_line": 1,
                "end_line": 20,
                "text": "def add(a, b):\n    return a + b\n\ndef subtract(a, b):\n    return a - b",
                "score": 0.95,
                "chunk_id": "calc_001"
            },
            {
                "file_path": "test_pipeline/demo_projects/calculator_demo/src/main.py",
                "start_line": 10,
                "end_line": 25,
                "text": "class Calculator:\n    def multiply(self, a, b):\n        return a * b",
                "score": 0.87,
                "chunk_id": "calc_002"
            },
            {
                "file_path": "tests/test_calculator.py",
                "start_line": 5,
                "end_line": 15,
                "text": "def test_calculator_operations():\n    calc = Calculator()\n    assert calc.add(2, 3) == 5",
                "score": 0.75,
                "chunk_id": "calc_003"
            }
        ]
    elif "agent" in query.lower():
        mock_results = [
            {
                "file_path": "agent/core/base_agent.py",
                "start_line": 1,
                "end_line": 30,
                "text": "class BaseAgent(ABC):\n    def __init__(self, model: str, component: str):",
                "score": 0.92,
                "chunk_id": "agent_001"
            },
            {
                "file_path": "agent/orchestrator/manager.py",
                "start_line": 50,
                "end_line": 70,
                "text": "class Manager(BaseAgent):\n    def orchestrate(self, task):",
                "score": 0.85,
                "chunk_id": "agent_002"
            }
        ]
    else:
        # Generic mock results
        mock_results = [
            {
                "file_path": "agent/llm.py",
                "start_line": 1,
                "end_line": 10,
                "text": f"# Mock result for query: {query}",
                "score": 0.5,
                "chunk_id": "generic_001"
            }
        ]
    
    # Apply file hints filter if provided
    if file_hints:
        filtered_results = []
        for result in mock_results:
            if any(hint in result["file_path"] for hint in file_hints):
                filtered_results.append(result)
        mock_results = filtered_results
    
    # Limit results
    mock_results = mock_results[:max_results]
    
    return {
        "query": query,
        "results": mock_results,
        "total_results": len(mock_results),
        "file_hints_used": file_hints,
        "status": "success"
    }


if __name__ == "__main__":
    main()
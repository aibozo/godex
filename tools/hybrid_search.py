#!/usr/bin/env python3
# tools/hybrid_search.py

import sys
import json
from pathlib import Path
from typing import Dict, Any, List

# Add the project root to Python path so we can import agent modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


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
        
        result = hybrid_search(query, file_hints, max_results)
        resp = {"exit_code": 0, "stdout": json.dumps(result), "stderr": ""}
        
    except Exception as e:
        resp = {"exit_code": 1, "stdout": "", "stderr": str(e)}

    print(json.dumps(resp))
    sys.exit(resp["exit_code"])


def hybrid_search(query: str, file_hints: List[str], max_results: int) -> Dict[str, Any]:
    """
    Perform hybrid search using the existing retrieval system.
    """
    try:
        # Import the existing hybrid retriever
        from agent.retrieval.orchestrator import HybridRetriever
        
        # Initialize retriever
        retriever = HybridRetriever()
        
        # Perform search
        results = retriever.fetch_context(query, top_n=max_results)
        
        # Filter by file hints if provided
        if file_hints:
            filtered_results = []
            for result in results:
                file_path = result.get("file_path", "")
                # Check if any hint matches the file path
                if any(hint in file_path for hint in file_hints):
                    filtered_results.append(result)
            results = filtered_results[:max_results]
        
        # Format results
        formatted_results = []
        for result in results:
            formatted_results.append({
                "file_path": result.get("file_path", ""),
                "start_line": result.get("start_line", 0),
                "end_line": result.get("end_line", 0),
                "text": result.get("text", ""),
                "score": result.get("score", 0.0),
                "chunk_id": result.get("chunk_id", "")
            })
        
        return {
            "query": query,
            "results": formatted_results,
            "total_results": len(formatted_results),
            "file_hints_used": file_hints,
            "status": "success"
        }
        
    except ImportError as e:
        return {
            "query": query,
            "results": [],
            "total_results": 0,
            "status": "error",
            "error": f"Retrieval system not available: {str(e)}"
        }
    except Exception as e:
        return {
            "query": query,
            "results": [],
            "total_results": 0,
            "status": "error", 
            "error": str(e)
        }


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
# coding-agent/tools/vector_search.py

import sys
import json
from typing import List, Any

# We use Chroma as a vector DB; the agent must have previously inserted embeddings.
import chromadb
from chromadb.config import Settings as ChromaSettings

def main():
    if len(sys.argv) != 2:
        msg = {"exit_code": 1, "stdout": "", "stderr": "Expected JSON arg"}
        print(json.dumps(msg)); sys.exit(1)

    try:
        args = json.loads(sys.argv[1])
        query = args.get("query")
        k = int(args.get("k", 5))
        collection_name = args.get("collection", "codebase")

        if not query:
            raise ValueError("Missing 'query'")

        # Connect to local Chroma instance (assumes ephemeral or persistent on disk)
        client = chromadb.Client(ChromaSettings(
            chroma_db_impl="duckdb+parquet",
            persist_directory="embeddings"
        ))
        col = client.get_collection(name=collection_name)
        # Perform search (returns list of dicts)
        results = col.query(query_texts=[query], n_results=k)
        # Structure output
        matches: List[Any] = []
        for idx, score in zip(results["ids"][0], results["distances"][0]):
            metadata = col.get(ids=[idx])["metadatas"][0]
            # Each metadata should contain {'path':..., 'start':..., 'end':...}
            matches.append({
                "id": idx,
                "score": score,
                "metadata": metadata
            })

        resp = {"exit_code": 0, "stdout": json.dumps(matches), "stderr": ""}
    except Exception as e:
        resp = {"exit_code": 1, "stdout": "", "stderr": str(e)}

    print(json.dumps(resp))
    sys.exit(resp["exit_code"])

if __name__ == "__main__":
    main()
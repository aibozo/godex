# coding-agent/tests/test_retrieval.py

import os
import sys
import shutil
import tempfile
import pytest
from pathlib import Path

from agent.retrieval.orchestrator import HybridRetriever
from agent.retrieval.chunker import chunk_file
from agent.retrieval.bm25_index import BM25Index

@pytest.fixture(scope="function")
def temp_repo(tmp_path, monkeypatch):
    """
    Create a temporary codebase with two small Python files:
      - hello.py containing a function 'def greet(): return "hello"'
      - math_utils.py containing 'def add(a, b): return a + b'
    Then monkeypatch agent_home to this temp dir.
    """
    # Create directory structure
    repo = tmp_path / "repo"
    repo.mkdir()
    # Create hello.py
    hello = repo / "hello.py"
    hello.write_text("def greet():\n    return 'hello'\n")
    # Create math_utils.py
    math_utils = repo / "math_utils.py"
    math_utils.write_text("def add(a, b):\n    return a + b\n\ndef multiply(x, y):\n    return x * y\n")
    # Create .cokeydex.yml with minimal config
    agent_yml = repo / ".cokeydex.yml"
    agent_yml.write_text("""
openai_api_key: ""
anthropic_api_key: ""
cost_cap_daily: 20.0
memory_summarise_threshold: 1000
tools_allowed:
  - read_file
  - write_diff
  - run_tests
  - static_analyze
  - grep
  - vector_search
retrieval:
  bm25:
    index_dir: "bm25_index"
    ngram_range: [1, 1]
    max_features: 1000
  chunker:
    max_tokens: 100
    overlap_tokens: 10
  embeddings:
    collection_name: "codebase"
    model: "stub"
""")
    # Monkeypatch agent_home to repo
    monkeypatch.setenv("AGENT_HOME", str(repo))
    return repo

def test_chunker(temp_repo):
    """Test the file chunking functionality"""
    os.chdir(temp_repo)
    hello_py = temp_repo / "hello.py"
    chunks = chunk_file(hello_py)
    
    assert len(chunks) >= 1  # Small file should be at least one chunk
    chunk = chunks[0]
    assert chunk["file_path"].endswith("hello.py")
    assert chunk["start_line"] == 1
    assert chunk["end_line"] == 2
    assert "def greet():" in chunk["text"]
    assert "return 'hello'" in chunk["text"]

def test_index_and_bm25_query(temp_repo):
    """Test BM25 index creation and querying"""
    os.chdir(temp_repo)
    retriever = HybridRetriever()
    retriever.index_codebase(temp_repo)

    # BM25 index files should exist in bm25_index/
    bm25_dir = retriever.bm25.index_dir
    assert bm25_dir.exists(), f"BM25 index dir {bm25_dir} does not exist"
    assert (bm25_dir / "vectorizer.joblib").exists()
    assert (bm25_dir / "matrix.npz").exists()
    assert (bm25_dir / "metadata.pkl").exists()
    assert (bm25_dir / "chunk_texts.pkl").exists()

    # Query BM25 for "greet"
    results = retriever.bm25.query("greet", top_n=1)
    assert len(results) == 1
    chunk_id, score = results[0]
    meta = retriever.bm25.metadata[chunk_id]
    assert meta["file_path"].endswith("hello.py")
    # Ensure that chunk covers line numbers including 'def greet()'
    assert meta["start_line"] == 1

def test_hybrid_fetch(temp_repo):
    """Test hybrid retrieval combining BM25 and vector search"""
    os.chdir(temp_repo)
    retriever = HybridRetriever()
    retriever.index_codebase(temp_repo)

    # fetch_context for "add numbers"
    # Expect to retrieve chunk from math_utils.py
    res_list = retriever.fetch_context("add numbers", top_n=1, bm25_k=2)
    assert len(res_list) == 1
    item = res_list[0]
    assert item["file_path"].endswith("math_utils.py")
    assert "add(a, b)" in item["text"]

def test_chroma_collection(temp_repo):
    """Test Chroma vector database collection"""
    os.chdir(temp_repo)
    retriever = HybridRetriever()
    retriever.index_codebase(temp_repo)

    # Directly query Chroma for chunk 'greet'
    # We know chunk_id for greet is in metadata where file_path == "hello.py"
    greet_chunk_ids = [cid for cid, m in retriever.bm25.metadata.items() if m["file_path"].endswith("hello.py")]
    assert len(greet_chunk_ids) >= 1
    cid = greet_chunk_ids[0]
    # Fetch from Chroma by id
    col = retriever.code_col
    result = col.get(ids=[str(cid)], include=["metadatas", "documents"])
    assert result["documents"][0].startswith("def greet")

def test_multiple_file_types(temp_repo):
    """Test indexing multiple file types"""
    os.chdir(temp_repo)
    
    # Create a JavaScript file
    js_file = temp_repo / "utils.js"
    js_file.write_text("function sayHello(name) {\n    return `Hello, ${name}!`;\n}")
    
    retriever = HybridRetriever()
    retriever.index_codebase(temp_repo)
    
    # Should have chunks from both Python and JS files
    total_chunks = len(retriever.bm25.metadata)
    assert total_chunks >= 3  # hello.py, math_utils.py, utils.js
    
    # Query for JavaScript function
    results = retriever.bm25.query("sayHello", top_n=1)
    assert len(results) == 1
    chunk_id, score = results[0]
    meta = retriever.bm25.metadata[chunk_id]
    assert meta["file_path"].endswith("utils.js")

def test_empty_index(temp_repo):
    """Test behavior with empty codebase"""
    os.chdir(temp_repo)
    # Remove all code files
    for f in temp_repo.glob("*.py"):
        f.unlink()
    
    retriever = HybridRetriever()
    retriever.index_codebase(temp_repo)
    
    # Should handle empty index gracefully
    results = retriever.fetch_context("test query", top_n=5)
    assert results == []
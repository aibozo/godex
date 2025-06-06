# coding-agent/agent/memory/vector_store.py

import uuid
import datetime
from typing import Dict, Any, List, Optional
import chromadb
from chromadb.config import Settings as ChromaSettings
from agent.config import get_settings
from agent.memory.utils import read_file

# --------------------------------------------------------------------------------
# Initialize Chroma client (singleton pattern)
# --------------------------------------------------------------------------------

_client: Optional[chromadb.Client] = None

def get_chroma_client() -> chromadb.Client:
    global _client
    if _client is None:
        settings = get_settings()
        persist_dir = str(settings.agent_home / "embeddings")
        # Use new Chroma API - PersistentClient instead of deprecated Client
        _client = chromadb.PersistentClient(path=persist_dir)
    return _client

# --------------------------------------------------------------------------------
# Ensure that the 'memory' collection exists
# --------------------------------------------------------------------------------

def get_memory_collection():
    client = get_chroma_client()
    try:
        return client.get_collection(name="memory")
    except Exception:
        return client.create_collection(name="memory")

# --------------------------------------------------------------------------------
# Insert a new memory snippet (summary or note) into the 'memory' collection.
# --------------------------------------------------------------------------------

def insert_memory_item(
    text: str,
    metadata: Dict[str, Any]
) -> str:
    """
    Inserts `text` with associated `metadata` into the memory collection.
    Returns the generated item_id (UUID).
    """
    col = get_memory_collection()
    item_id = str(uuid.uuid4())
    # Create an embedding using a local or OpenAI embedder. For simplicity, we delegate:
    embedding = _embed_text(text)
    col.add(
        ids=[item_id],
        embeddings=[embedding],
        metadatas=[metadata],
        documents=[text]
    )
    return item_id

# --------------------------------------------------------------------------------
# Example placeholder for embedding text. In real life, call OpenAI/CreateEmbedding or local model.
# --------------------------------------------------------------------------------

def _embed_text(text: str) -> List[float]:
    """
    Returns a vector embedding for `text`. 
    Replace with actual embedding call (e.g., OpenAI or a local embedder).
    """
    settings = get_settings()
    # Example using OpenAI: (Assuming openai-py installed)
    # 
    # import openai
    # client = openai.OpenAI(api_key=settings.openai_api_key)
    # resp = client.embeddings.create(
    #     model="text-embedding-3-small",
    #     input=text
    # )
    # return resp.data[0].embedding
    #
    # For Phase III, we can stub out with a random vector or length-1 vector.
    # Use 384 dimensions for text-embedding-3-small
    return [0.0] * 384  # placeholder embedding

# --------------------------------------------------------------------------------
# Query memory collection; return top‐k items with metadata.
# --------------------------------------------------------------------------------

def query_memory(query: str, k: int = 5) -> List[Dict[str, Any]]:
    """
    Return a list of up to k memory items matching `query`. 
    Each item: {"id": ..., "score": ..., "document": ..., "metadata": {...}}
    """
    col = get_memory_collection()
    embedding = _embed_text(query)
    results = col.query(
        query_embeddings=[embedding],
        n_results=k
    )
    items = []
    if results["ids"] and len(results["ids"]) > 0:
        ids = results["ids"][0]
        distances = results["distances"][0]
        metadatas = results["metadatas"][0]
        documents = results["documents"][0]
        
        for idx, dist, meta, doc in zip(ids, distances, metadatas, documents):
            items.append({
                "id": idx,
                "score": dist,
                "metadata": meta,
                "document": doc
            })
    return items
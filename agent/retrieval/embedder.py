# coding-agent/agent/retrieval/embedder.py

from typing import List
from agent.config import get_settings

# --------------------------------------------------------------------------------
# Placeholder embedder: returns a fixed‐length zero vector or a random vector.
# Replace this function when real embeddings are needed.
# --------------------------------------------------------------------------------

def embed_text(text: str) -> List[float]:
    """
    Return an embedding for `text`. Currently a stub: returns zero vector.
    """
    settings = get_settings()
    # In Phase VII, do something like:
    # import openai
    # client = openai.OpenAI(api_key=settings.openai_api_key)
    # resp = client.embeddings.create(
    #     model=settings.retrieval["embeddings"]["model"],
    #     input=text
    # )
    # return resp.data[0].embedding

    # For now, use a fixed‐length zero vector (length 384 for text-embedding-3-small)
    # OpenAI's text-embedding-3-small has 384 dimensions
    return [0.0] * 384
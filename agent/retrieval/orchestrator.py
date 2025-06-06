# coding-agent/agent/retrieval/orchestrator.py

import pickle
from pathlib import Path
from typing import List, Dict, Any

import chromadb
import numpy as np

from agent.config import get_settings
from agent.retrieval.bm25_index import BM25Index
from agent.retrieval.chunker import chunk_file
from agent.retrieval.embedder import embed_text

# --------------------------------------------------------------------------------
# HybridRetriever: Combines BM25 & vector retrieval for "codebase"
# --------------------------------------------------------------------------------

class HybridRetriever:
    def __init__(self):
        self.settings = get_settings()
        # 1. BM25 index
        self.bm25 = BM25Index()

        # 2. Chroma client for codebase collection
        persist_dir = str(self.settings.agent_home / "embeddings")
        self.client = chromadb.PersistentClient(path=persist_dir)
        
        collection_name = self.settings.retrieval["embeddings"]["collection_name"]
        try:
            self.code_col = self.client.get_collection(name=collection_name)
        except Exception:
            self.code_col = self.client.create_collection(name=collection_name)

    def index_codebase(self, root_dir: Path) -> None:
        """
        Build BM25 index and Chroma codebase embeddings from scratch.
        """
        # 1. BM25 build: also saves chunk_texts.pkl
        self.bm25.build_index(root_dir)

        # 2. Clear existing embeddings in Chroma collection
        existing_ids = self.code_col.get()["ids"]
        if existing_ids:
            self.code_col.delete(ids=existing_ids)

        # 3. Insert embeddings for each chunk
        # Note: BM25 metadata has chunk_id → {file_path, start_line, end_line}
        for chunk_id, meta in self.bm25.metadata.items():
            chunk_text = self.bm25.chunk_texts[chunk_id]
            embedding = embed_text(chunk_text)
            # Metadata for Chroma: include file_path, lines, chunk_id
            data = {
                "file_path": meta["file_path"],
                "start_line": meta["start_line"],
                "end_line": meta["end_line"],
                "chunk_id": chunk_id
            }
            # Use chunk_id as the Chroma document id (must be string)
            self.code_col.add(
                ids=[str(chunk_id)],
                embeddings=[embedding],
                metadatas=[data],
                documents=[chunk_text]
            )

    def fetch_context(self, query: str, top_n: int = 5, bm25_k: int = 50) -> List[Dict[str, Any]]:
        """
        Hybrid retrieval: 
          1. BM25 → get top bm25_k chunks.
          2. Get embeddings for query + those chunks.
          3. Rerank by vector similarity via Chroma query.
        Returns top_n chunks with metadata and score.
        """
        # Check if index is built
        if self.bm25.vectorizer is None or self.bm25.matrix is None:
            return []
            
        # 1. BM25 step
        bm25_results = self.bm25.query(query, top_n=bm25_k)
        if not bm25_results:
            return []
            
        candidate_ids = [cid for cid, _score in bm25_results]

        # 2. Use Chroma to rerank: 
        #    Query Chroma for top_n among candidate_ids only.
        #    Unfortunately, Chroma's API doesn't support restricting to a subset directly.
        #    Workaround: retrieve all candidate embeddings, compute similarity client-side.

        # Fetch embeddings of candidates
        # Chroma query by IDs to get embeddings
        str_ids = [str(cid) for cid in candidate_ids]
        res = self.code_col.get(ids=str_ids, include=["embeddings", "metadatas", "documents"])
        
        if not res["ids"]:
            return []
            
        docs = res["documents"]
        metas = res["metadatas"]
        embs = res["embeddings"]

        # Compute query embedding
        q_emb = embed_text(query)

        # Compute cosine similarity manually
        scores = []
        for idx, emb in enumerate(embs):
            # emb and q_emb are lists of floats
            emb_arr = np.array(emb)
            q_arr = np.array(q_emb)
            # Avoid zero-division
            emb_norm = np.linalg.norm(emb_arr)
            q_norm = np.linalg.norm(q_arr)
            if emb_norm == 0 or q_norm == 0:
                sim = 0.0
            else:
                sim = float(np.dot(emb_arr, q_arr) / (emb_norm * q_norm))
            scores.append((candidate_ids[idx], sim))

        # Sort by sim desc
        scores.sort(key=lambda x: x[1], reverse=True)
        top_scores = scores[:top_n]

        # Build return objects
        results: List[Dict[str, Any]] = []
        for cid, score in top_scores:
            meta = self.bm25.metadata[cid]
            text = self.bm25.chunk_texts[cid]
            results.append({
                "chunk_id": cid,
                "file_path": meta["file_path"],
                "start_line": meta["start_line"],
                "end_line": meta["end_line"],
                "text": text,
                "score": score
            })
        return results

    def update_file(self, file_path: Path) -> None:
        """
        Recompute chunks and embeddings for the given file only, updating both BM25 and Chroma.
        Steps:
          1. Identify old chunk_ids belonging to file_path; delete them from BM25 and Chroma.
          2. Chunk new file → get new chunks with new chunk_ids. 
             (For simplicity, build BM25 index from scratch: Phase V will optimize incremental BM25.)
          3. Insert new embeddings for each chunk.
        """
        # Simplest: rebuild entire codebase index (slow). 
        # Advanced: implement incremental deletes/inserts.

        # For Phase IV: just call index_codebase from root_dir again.
        root_dir = Path(self.settings.agent_home)
        self.index_codebase(root_dir)
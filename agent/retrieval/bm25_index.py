# coding-agent/agent/retrieval/bm25_index.py

import os
import pickle
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import joblib

from agent.config import get_settings
from agent.retrieval.chunker import chunk_file

# --------------------------------------------------------------------------------
# Directory and filenames for BM25 index persistence
# --------------------------------------------------------------------------------

class BM25Index:
    def __init__(self):
        settings = get_settings()
        self.index_dir = Path(settings.agent_home) / settings.retrieval["bm25"]["index_dir"]
        self.index_dir.mkdir(parents=True, exist_ok=True)
        
        self.vectorizer_path = self.index_dir / "vectorizer.joblib"
        self.matrix_path = self.index_dir / "matrix.npz"
        self.metadata_path = self.index_dir / "metadata.pkl"
        self.chunk_texts_path = self.index_dir / "chunk_texts.pkl"
        
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.matrix = None  # sparse matrix [num_chunks x vocab_size]
        self.metadata: Dict[int, Dict[str, Any]] = {}
        self.chunk_texts: Dict[int, str] = {}
        # id → {"file_path":..., "start_line":..., "end_line":..., "text":...}

        if self._check_index_exists():
            self._load_index()
        else:
            self.vectorizer = None
            self.matrix = None

    def _check_index_exists(self) -> bool:
        return (self.vectorizer_path.exists() and 
                self.matrix_path.exists() and 
                self.metadata_path.exists() and
                self.chunk_texts_path.exists())

    def build_index(self, root_dir: Path) -> None:
        """
        Walk `root_dir`, chunk each code file, and build BM25 index.
        Persists vectorizer, matrix, and metadata to disk.
        """
        settings = get_settings()
        all_texts: List[str] = []
        self.metadata = {}
        self.chunk_texts = {}
        idx = 0

        # Support multiple file types
        file_patterns = ["*.py", "*.js", "*.ts", "*.jsx", "*.tsx", "*.java", "*.cpp", "*.c", "*.h", "*.go", "*.rs"]
        
        for pattern in file_patterns:
            for file_path in root_dir.rglob(pattern):
                # Skip hidden files and directories
                if any(part.startswith('.') for part in file_path.parts):
                    continue
                # Skip node_modules, venv, etc.
                if any(skip in file_path.parts for skip in ['node_modules', 'venv', '__pycache__', 'dist', 'build']):
                    continue
                    
                try:
                    chunks = chunk_file(file_path)
                    for ch in chunks:
                        all_texts.append(ch["text"])
                        self.metadata[idx] = {
                            "file_path": ch["file_path"],
                            "start_line": ch["start_line"],
                            "end_line": ch["end_line"]
                        }
                        self.chunk_texts[idx] = ch["text"]
                        idx += 1
                except Exception as e:
                    print(f"Warning: Failed to chunk {file_path}: {e}")

        if not all_texts:
            print("Warning: No code files found to index")
            return

        # Create TF-IDF vectorizer approximating BM25 with k1=1.5, b=0.75 equivalent
        self.vectorizer = TfidfVectorizer(
            ngram_range=tuple(settings.retrieval["bm25"]["ngram_range"]),
            max_features=settings.retrieval["bm25"]["max_features"],
            norm="l2",
            use_idf=True,
            smooth_idf=True,
            sublinear_tf=True
        )
        self.matrix = self.vectorizer.fit_transform(all_texts)

        # Persist to disk
        joblib.dump(self.vectorizer, self.vectorizer_path)
        joblib.dump(self.matrix, self.matrix_path)
        with open(self.metadata_path, "wb") as fh:
            pickle.dump(self.metadata, fh)
        with open(self.chunk_texts_path, "wb") as fh:
            pickle.dump(self.chunk_texts, fh)

    def _load_index(self) -> None:
        """
        Load pre-built vectorizer, matrix, and metadata from disk.
        """
        self.vectorizer = joblib.load(self.vectorizer_path)
        self.matrix = joblib.load(self.matrix_path)
        with open(self.metadata_path, "rb") as fh:
            self.metadata = pickle.load(fh)
        with open(self.chunk_texts_path, "rb") as fh:
            self.chunk_texts = pickle.load(fh)

    def query(self, query_text: str, top_n: int = 10) -> List[Tuple[int, float]]:
        """
        Return top_n matches as a list of (chunk_id, score), sorted descending.
        """
        if self.vectorizer is None or self.matrix is None:
            raise RuntimeError("BM25 index not built or loaded")

        q_vec = self.vectorizer.transform([query_text])  # 1 x vocab_size
        # Compute cosine similarity against all chunks
        scores = cosine_similarity(q_vec, self.matrix).flatten()  # shape: [num_chunks]
        # Get top_n indices
        best_idx = scores.argsort()[::-1][:top_n]
        return [(int(i), float(scores[i])) for i in best_idx]

    def get_chunk_text(self, chunk_id: int) -> str:
        """Get the text content of a specific chunk by ID"""
        return self.chunk_texts.get(chunk_id, "")
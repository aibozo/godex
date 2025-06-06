"""Retrieval layer for hybrid BM25 + vector search over codebase"""

from .orchestrator import HybridRetriever

__all__ = ["HybridRetriever"]
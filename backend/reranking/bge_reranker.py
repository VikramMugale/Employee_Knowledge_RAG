"""Unused. Hybrid retrieval uses Voyage/Atlas (`voyage_reranker`), not a simulated BGE CrossEncoder."""
from backend.reranking.voyage_reranker import VoyageReranker, voyage_reranker

BGEReranker = VoyageReranker
bge_reranker = voyage_reranker

# ADR-003: Two-Stage Reranking Architecture (Voyage / Atlas)

## Status
Accepted

## Context
RRF fusion returns Top 30 candidate chunks. Feeding 30 chunks directly to the LLM increases latency, cost, and lost-in-the-middle risk.

## Decision
Rerank fused candidates with the Voyage rerank API on MongoDB Atlas (`https://ai.mongodb.com/v1/rerank`), default model `rerank-2.5`. Authenticate with the Atlas model API key in `VOYAGE_API_KEY`. If the key or API is unavailable, fall back to lexical overlap.

## Rationale
- Rerank scores `(query, chunk)` pairs more precisely than embedding similarity or BM25 alone.
- Atlas model keys target `ai.mongodb.com`; the voyageai SDK is not required.
- Reduces Top 30 to Top 8 before Gemini generation.

# ADR-002: Hybrid Retrieval Strategy (Dense + Sparse BM25 with RRF)

## Status
Accepted

## Context
Employee policy queries frequently contain exact section numbers (e.g., "Section 2.1 Privilege Leave"), policy document IDs ("POL-HR-001"), acronyms ("POSH", "PL", "WFH"), and specific numeric parameters alongside natural language questions ("How much leave carry forward is allowed?"). Vector search alone struggles with exact term/code matching, while BM25 keyword search struggles with semantic intent.

## Decision
We implement a **Hybrid Retrieval** engine combining Qdrant dense vector search with OpenSearch BM25 lexical keyword search, aggregated using **Reciprocal Rank Fusion (RRF)**.

## Rationale
- **Reciprocal Rank Fusion (RRF)**: Combines candidate lists based on rank position rather than raw non-comparable similarity scores:
  \[
  RRF\_Score(d) = \sum_{m \in M} \frac{1}{k + r_m(d)}
  \]
  where $k=60$ and $r_m(d)$ is document rank in retriever $m$.
- **High Recall**: Guarantees high Recall@K for both semantic queries and exact keyword/policy-id queries.

## Consequences
- Requires dual query execution to Qdrant and OpenSearch.
- Configurable top-K hyperparameters (`vector_top_k: 30`, `keyword_top_k: 30`, `fusion_top_k: 30`).

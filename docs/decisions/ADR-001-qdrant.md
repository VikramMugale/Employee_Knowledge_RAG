# ADR-001: Selection of Qdrant as Primary Dense Vector Store

## Status
Accepted

## Context
The Employee RAG Platform requires a production vector database to store and search dense vector embeddings for policy document chunks. The vector database must support payload metadata filtering (ACL, department, versioning), HNSW indexing, multi-tenant payload isolation, fast upserts, and low-latency similarity search.

## Decision
We select **Qdrant** as the primary dense vector store.

## Rationale
- **Payload Filtering First**: Qdrant executes metadata filtering (e.g. `access_level IN [...] AND department = 'HR'`) during vector index traversal rather than post-filtering, guaranteeing 100% compliance with access control lists (ACL) without recall loss.
- **Performance**: Written in Rust, offering low CPU and memory footprints with HNSW graph indexing.
- **Python Integration**: Robust `qdrant-client` Python SDK with async and sync support.
- **Containerization**: Official Docker images for local `docker-compose` setup and Cloud/K8s deployment options.

## Consequences
- Requires Qdrant service deployment in Docker/Kubernetes.
- Vector search will be paired with OpenSearch for lexical keyword search (Hybrid retrieval).

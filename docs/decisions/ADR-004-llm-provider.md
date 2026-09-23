# ADR-004: Selection of Google Gemini API (`gemini-2.5-flash` & `text-embedding-004`)

## Status
Accepted

## Context
The platform requires an enterprise LLM generation and embedding engine for query processing, context-grounded response generation, and citation formatting. Enterprise requirements mandate decoupling provider code from business logic so models can be swapped or failed over without refactoring.

## Decision
Define an abstract `LLMProvider` interface and provide **Google Gemini API (`gemini-2.5-flash` & `text-embedding-004`)** as the primary concrete provider implementation (`backend/llm/providers.py`).

## Rationale
- High intelligence, low latency, and cost-effective generation via `gemini-2.5-flash`.
- Native 768-dimensional text embeddings via `text-embedding-004`.
- Streaming support via Server-Sent Events (SSE).
- Interface-decoupled implementation allowing easy fallback to Azure or local models.

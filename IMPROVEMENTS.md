# Improvements applied (Redis excluded)

Implemented against the review notes. Redis is still unused on purpose.

## Correctness
- Section-aware chunking with token budget (~550) and overlap (~80)
- Query rewrite + intent hints, including follow-up pronoun expansion
- Conversation memory for last user turns (in-process, no Redis)
- Claim-to-chunk citation alignment via token overlap
- Evaluation uses lexical groundedness, truth overlap, retrieval hit rate

## Reliability
- Hash embeddings are blocked when `ENVIRONMENT=production` and `ALLOW_HASH_EMBEDDINGS=false`
- Document lifecycle after ingest is `ACTIVE`
- Chunk metadata includes `lifecycle_state` for version-aware retrieval
- Background ingest via in-process asyncio queue (`POST /api/v1/documents`, `GET /api/v1/documents/jobs/{id}`)
- Readiness reports `degraded` when search/LLM backends fall back

## Safety
- PII redaction runs at ingest, not only on model output
- In-memory rate limit middleware (`RATE_LIMIT_PER_MINUTE`, default 60)

## Not done (explicit)
- Redis caching / Redis job broker

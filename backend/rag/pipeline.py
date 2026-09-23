"""
RAG Orchestration Pipeline integrating authorization, hybrid retrieval, Gemini generation,
citation creation, guardrails, and tracing.
"""

import json
from typing import AsyncGenerator, List, Optional
from backend.rag.models import RAGQuery, RAGResponse
from backend.retrieval.models import RetrievalQuery, CandidateChunk
from backend.retrieval.hybrid_search import hybrid_retriever
from backend.llm.providers import llm_provider
from backend.llm.models import LLMRequest, LLMMessage
from backend.citations.generator import citation_generator
from backend.guardrails.prompt_injection import prompt_injection_guardrail
from backend.guardrails.document_security import document_content_guardrail
from backend.guardrails.pii import pii_guardrail
from backend.auth.authorization import authorization_engine
from backend.auth.models import Permission
from llmops.prompts.prompt_manager import prompt_manager
from observability.tracing.telemetry import telemetry_tracer
from backend.config.settings import settings
from backend.config.logging import logger
from backend.rag.query_rewrite import rewrite_query
from backend.rag.conversation import conversation_memory


NO_ANSWER_TEXT = (
    "I do not have enough information in the available company policies to answer your question."
)


class RAGPipeline:
    async def execute(self, query: RAGQuery) -> RAGResponse:
        trace_id = telemetry_tracer.start_trace(
            name="rag_query_execution",
            user_id=query.user_context.user_id,
            metadata={"department": query.user_context.department},
        )
        blocked = await self._check_input_guardrail(query, trace_id)
        if blocked is not None:
            return blocked
        conversation_memory.add_user_turn(query.conversation_id or "", query.query_text)
        retrieved_chunks = await self._retrieve(query, trace_id)
        if not retrieved_chunks:
            logger.info(f"[NO-ANSWER TRIGGERED] trace_id={trace_id} for query '{query.query_text}'")
            return RAGResponse(
                answer=NO_ANSWER_TEXT,
                citations=[],
                no_answer_flag=True,
                conversation_id=query.conversation_id,
                trace_id=trace_id,
            )
        sanitized_chunks = await self._sanitize_chunks(retrieved_chunks)
        llm_response = await llm_provider.generate(self._build_llm_request(query, sanitized_chunks))
        answer = await self._sanitize_output(llm_response.content)
        no_answer = NO_ANSWER_TEXT.lower() in answer.lower()
        citations = [] if no_answer else await citation_generator.generate_citations(answer, sanitized_chunks)
        telemetry_tracer.log_span(
            trace_id=trace_id,
            span_name="llm_generation",
            inputs={"messages_count": 2, "provider": "gemini"},
            outputs={"total_tokens": llm_response.total_tokens},
        )
        return RAGResponse(
            answer=answer,
            citations=citations,
            no_answer_flag=no_answer,
            conversation_id=query.conversation_id,
            trace_id=trace_id,
        )

    async def stream(self, query: RAGQuery) -> AsyncGenerator[str, None]:
        trace_id = telemetry_tracer.start_trace(
            name="rag_query_stream",
            user_id=query.user_context.user_id,
            metadata={"department": query.user_context.department},
        )
        yield self._sse("metadata", {"status": "processing", "user": query.user_context.user_id, "trace_id": trace_id})
        blocked = await self._check_input_guardrail(query, trace_id)
        if blocked is not None:
            yield self._sse("token", {"token": blocked.answer})
            yield self._sse("done", {"status": "blocked", "no_answer": True, "trace_id": trace_id})
            return
        conversation_memory.add_user_turn(query.conversation_id or "", query.query_text)
        retrieved_chunks = await self._retrieve(query, trace_id)
        if not retrieved_chunks:
            yield self._sse("token", {"token": NO_ANSWER_TEXT})
            yield self._sse("done", {"status": "completed", "no_answer": True, "trace_id": trace_id})
            return
        sanitized_chunks = await self._sanitize_chunks(retrieved_chunks)
        citations = await citation_generator.generate_citations("", sanitized_chunks)
        yield self._sse("citations", [citation.model_dump() for citation in citations])
        assembled = ""
        async for token in llm_provider.stream(self._build_llm_request(query, sanitized_chunks, stream=True)):
            assembled += token
            yield self._sse("token", {"token": token})
        redacted = await self._sanitize_output(assembled)
        if redacted != assembled:
            yield self._sse("redacted_answer", {"answer": redacted})
        yield self._sse("done", {"status": "completed", "no_answer": False, "trace_id": trace_id})

    async def _check_input_guardrail(self, query: RAGQuery, trace_id: str) -> Optional[RAGResponse]:
        injection = await prompt_injection_guardrail.validate(query.query_text)
        if injection.passed:
            return None
        logger.info(f"[GUARDRAIL BLOCK] trace_id={trace_id} reason={injection.reason}")
        return RAGResponse(
            answer=NO_ANSWER_TEXT,
            citations=[],
            no_answer_flag=True,
            conversation_id=query.conversation_id,
            trace_id=trace_id,
        )

    async def _retrieve(self, query: RAGQuery, trace_id: str) -> List[CandidateChunk]:
        if not authorization_engine.authorize_access(query.user_context, Permission.READ_PUBLIC_POLICY):
            logger.info(f"[AUTHZ DENY] trace_id={trace_id} user={query.user_context.user_id}")
            return []
        history = conversation_memory.recent_user_turns(query.conversation_id or "")[:-1]
        rewritten, _intent = rewrite_query(query.query_text, history)
        filters = acl_payload(query)
        if settings.active_versions_only:
            filters["lifecycle_state"] = "ACTIVE"
        retrieval_query = RetrievalQuery(
            query_text=rewritten,
            user_context=query.user_context,
            vector_top_k=settings.retrieval.vector_top_k,
            keyword_top_k=settings.retrieval.keyword_top_k,
            fusion_top_k=settings.retrieval.fusion_top_k,
            metadata_filters=filters,
        )
        retrieved_chunks = await hybrid_retriever.retrieve(retrieval_query)
        telemetry_tracer.log_span(
            trace_id=trace_id,
            span_name="hybrid_retrieval",
            inputs={"query": query.query_text},
            outputs={"count": len(retrieved_chunks)},
            scores={"retriever_top_score": _top_score(retrieved_chunks)},
        )
        return retrieved_chunks

    async def _sanitize_chunks(self, chunks: List[CandidateChunk]) -> List[CandidateChunk]:
        sanitized: List[CandidateChunk] = []
        for chunk in chunks:
            result = await document_content_guardrail.validate(chunk.content)
            clone = chunk.model_copy(deep=True)
            clone.content = result.sanitized_content or chunk.content
            sanitized.append(clone)
        return sanitized

    def _build_llm_request(self, query: RAGQuery, chunks: List[CandidateChunk], stream: bool = False) -> LLMRequest:
        context_str = "\n\n---\n\n".join(
            [f"[Source: {chunk.metadata.document_title} - {chunk.metadata.section_title}]\n{chunk.content}" for chunk in chunks]
        )
        history = conversation_memory.recent_user_turns(query.conversation_id or "")
        history_block = ""
        if len(history) > 1:
            prior = " | ".join(history[:-1][-3:])
            history_block = f"\nPrior user questions in this conversation: {prior}\n"
        system_prompt = prompt_manager.get_prompt("rag_system_prompt").template.format(context=context_str)
        user_content = f"{history_block}{query.query_text}".strip()
        return LLMRequest(
            messages=[
                LLMMessage(role="system", content=system_prompt),
                LLMMessage(role="user", content=user_content),
            ],
            temperature=0.0,
            model=settings.gemini_model,
            stream=stream,
        )

    async def _sanitize_output(self, answer: str) -> str:
        result = await pii_guardrail.validate(answer)
        return result.sanitized_content or answer

    def _sse(self, event: str, data) -> str:
        return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def acl_payload(query: RAGQuery) -> dict:
    return {"access_levels": query.user_context.allowed_access_levels}


def _top_score(chunks: List[CandidateChunk]) -> float:
    if not chunks:
        return 0.0
    first = chunks[0]
    return first.reranker_score or first.fusion_score or first.dense_score or 0.0


rag_pipeline = RAGPipeline()

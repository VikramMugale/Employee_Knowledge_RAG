"""
Evaluation runner with lexical groundedness, retrieval hit-rate, and no-answer checks.
"""

from typing import List, Dict, Any
from llmops.evaluations.base import Evaluator, EvaluationCase, EvaluationResult, FailureCategory
from backend.rag.models import RAGQuery, RAGResponse
from backend.rag.pipeline import rag_pipeline
from backend.auth.models import UserContext, Role
from llmops.datasets.golden_dataset import GOLDEN_TEST_CASES
from backend.config.logging import logger
from backend.citations.generator import _tokens


class BaselineEvaluator(Evaluator):
    async def evaluate_case(self, case: EvaluationCase, answer: str, context_chunks: List[str]) -> EvaluationResult:
        no_answer_target = "do not have enough information" in case.ground_truth_answer.lower()
        no_answer_actual = "do not have enough information" in answer.lower()
        no_answer_correct = no_answer_target == no_answer_actual
        answer_tokens = _tokens(answer)
        truth_tokens = _tokens(case.ground_truth_answer)
        context_tokens = set()
        for chunk in context_chunks:
            context_tokens |= _tokens(chunk)
        if no_answer_target:
            faithfulness = 1.0 if no_answer_correct else 0.0
            relevance = 1.0 if no_answer_correct else 0.2
            recall = 1.0 if no_answer_correct else 0.0
            citation_accuracy = 1.0 if no_answer_correct else 0.0
        else:
            overlap_truth = len(answer_tokens & truth_tokens) / max(1, len(truth_tokens))
            grounded = len(answer_tokens & context_tokens) / max(1, len(answer_tokens)) if answer_tokens else 0.0
            faithfulness = round(max(overlap_truth, grounded * 0.8), 4) if not no_answer_actual else 0.2
            relevance = round(overlap_truth, 4)
            expected = (case.expected_section or "").lower()
            recall = 1.0 if any(expected and expected.split()[0] in chunk.lower() for chunk in context_chunks) else overlap_truth
            citation_accuracy = 1.0 if grounded >= 0.2 or overlap_truth >= 0.35 else 0.4
        failure_cat = FailureCategory.NONE
        if not no_answer_correct:
            failure_cat = FailureCategory.GENERATION_FAILURE if not case.is_out_of_scope else FailureCategory.GUARDRAIL_FAILURE
        elif not case.is_out_of_scope and faithfulness < 0.5:
            failure_cat = FailureCategory.RETRIEVAL_FAILURE
        return EvaluationResult(
            case_id=case.id,
            question=case.question,
            generated_answer=answer,
            faithfulness_score=float(faithfulness),
            answer_relevance_score=float(relevance),
            context_recall_score=float(recall),
            citation_accuracy=float(citation_accuracy),
            no_answer_correct=no_answer_correct,
            failure_category=failure_cat,
            details={
                "context_chunks": len(context_chunks),
                "token_overlap_truth": round(len(answer_tokens & truth_tokens) / max(1, len(truth_tokens)), 4),
            },
        )

    async def run_suite(self) -> Dict[str, Any]:
        from backend.retrieval.vector_search import vector_retriever
        from backend.ingestion.pipeline import ingestion_pipeline
        import os
        if not getattr(vector_retriever, "_memory_chunks", []):
            seed_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "seed", "policies"))
            await ingestion_pipeline.ingest_directory(seed_dir)
        user_ctx = UserContext(
            user_id="eval_user",
            role=Role.EMPLOYEE,
            department="General",
            location="Global",
            employment_type="full_time",
            allowed_access_levels=["PUBLIC_INTERNAL"],
        )
        results: List[EvaluationResult] = []
        hits = 0
        for case in GOLDEN_TEST_CASES:
            rag_query = RAGQuery(query_text=case.question, user_context=user_ctx)
            response: RAGResponse = await rag_pipeline.execute(rag_query)
            contexts = [citation.snippet for citation in response.citations]
            if case.expected_section and any(
                case.expected_section.split()[0].lower() in (citation.section_title or "").lower()
                for citation in response.citations
            ):
                hits += 1
            elif case.is_out_of_scope and response.no_answer_flag:
                hits += 1
            res = await self.evaluate_case(case, response.answer, contexts)
            results.append(res)
        avg_faithfulness = sum(r.faithfulness_score for r in results) / len(results)
        avg_recall = sum(r.context_recall_score for r in results) / len(results)
        no_answer_acc = sum(1 for r in results if r.no_answer_correct) / len(results)
        hit_rate = hits / len(results)
        summary = {
            "total_cases": len(results),
            "mean_faithfulness": round(avg_faithfulness, 4),
            "mean_context_recall": round(avg_recall, 4),
            "no_answer_accuracy": round(no_answer_acc, 4),
            "retrieval_hit_rate": round(hit_rate, 4),
            "cases": [r.model_dump() for r in results],
        }
        logger.info(
            "[EVALUATION SUITE COMPLETE] Cases: %s | Faithfulness: %s | Recall: %s | No-Answer: %s | HitRate: %s",
            summary["total_cases"],
            summary["mean_faithfulness"],
            summary["mean_context_recall"],
            summary["no_answer_accuracy"],
            summary["retrieval_hit_rate"],
        )
        return summary


baseline_evaluations = BaselineEvaluator()

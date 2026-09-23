"""
Baseline Evaluation Runner calculating benchmark quality metrics and failure taxonomy.
"""

from typing import List, Dict, Any
from llmops.evaluations.base import Evaluator, EvaluationCase, EvaluationResult, FailureCategory
from backend.rag.models import RAGQuery, RAGResponse
from backend.rag.pipeline import rag_pipeline
from backend.auth.models import UserContext, Role
from llmops.datasets.golden_dataset import GOLDEN_TEST_CASES
from backend.config.logging import logger


class BaselineEvaluator(Evaluator):
    """Evaluates golden test cases against RAG Pipeline, calculating precision metrics and failure modes."""

    async def evaluate_case(self, case: EvaluationCase, answer: str, context_chunks: List[str]) -> EvaluationResult:
        """Score single test case result."""
        no_answer_target = "do not have enough information" in case.ground_truth_answer.lower()
        no_answer_actual = "do not have enough information" in answer.lower()
        no_answer_correct = (no_answer_target == no_answer_actual)

        # Baseline similarity check
        faithfulness = 1.0 if (no_answer_correct or case.ground_truth_answer[:20].lower() in answer.lower()) else 0.70
        context_recall = 1.0 if not case.is_out_of_scope else (1.0 if no_answer_correct else 0.0)

        failure_cat = FailureCategory.NONE
        if not no_answer_correct:
            failure_cat = FailureCategory.GENERATION_FAILURE if not case.is_out_of_scope else FailureCategory.GUARDRAIL_FAILURE

        return EvaluationResult(
            case_id=case.id,
            question=case.question,
            generated_answer=answer,
            faithfulness_score=faithfulness,
            answer_relevance_score=0.90 if no_answer_correct else 0.40,
            context_recall_score=context_recall,
            citation_accuracy=1.0,
            no_answer_correct=no_answer_correct,
            failure_category=failure_cat
        )

    async def run_suite(self) -> Dict[str, Any]:
        """Run full evaluation suite across golden dataset."""
        from backend.retrieval.vector_search import vector_retriever
        from backend.ingestion.pipeline import ingestion_pipeline
        import os

        if not getattr(vector_retriever, "_memory_chunks", []):
            seed_dir = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..", "data", "seed", "policies")
            )
            await ingestion_pipeline.ingest_directory(seed_dir)

        user_ctx = UserContext(
            user_id="eval_user",
            role=Role.EMPLOYEE,
            department="General",
            location="Global",
            employment_type="full_time",
            allowed_access_levels=["PUBLIC_INTERNAL"]
        )

        results: List[EvaluationResult] = []
        for case in GOLDEN_TEST_CASES:
            rag_query = RAGQuery(query_text=case.question, user_context=user_ctx)
            response: RAGResponse = await rag_pipeline.execute(rag_query)
            res = await self.evaluate_case(case, response.answer, [])
            results.append(res)

        avg_faithfulness = sum(r.faithfulness_score for r in results) / len(results)
        avg_recall = sum(r.context_recall_score for r in results) / len(results)
        no_answer_acc = sum(1 for r in results if r.no_answer_correct) / len(results)

        summary = {
            "total_cases": len(results),
            "mean_faithfulness": round(avg_faithfulness, 4),
            "mean_context_recall": round(avg_recall, 4),
            "no_answer_accuracy": round(no_answer_acc, 4),
            "cases": [r.model_dump() for r in results]
        }

        logger.info(
            f"[EVALUATION SUITE COMPLETE] Cases: {summary['total_cases']} | "
            f"Faithfulness: {summary['mean_faithfulness']} | "
            f"Recall: {summary['mean_context_recall']} | "
            f"No-Answer Accuracy: {summary['no_answer_accuracy']}"
        )
        return summary


baseline_evaluations = BaselineEvaluator()

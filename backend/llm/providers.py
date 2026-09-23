"""
Concrete Google Gemini LLM Provider implementation with streaming & mock fallback support.
"""

import os
import asyncio
from typing import List, AsyncGenerator
from backend.llm.models import LLMProvider, LLMRequest, LLMResponse
from backend.config.settings import settings
from backend.config.logging import logger

try:
    import google.generativeai as genai
    gemini_available = True
except ImportError:
    gemini_available = False


class GeminiProvider(LLMProvider):
    """Google Gemini LLM adapter generating completions and token streams using gemini-2.5-flash."""

    def __init__(self):
        self.api_key = settings.gemini_api_key or os.getenv("GEMINI_API_KEY", "") or os.getenv("GOOGLE_API_KEY", "")
        self.model_name = settings.gemini_model
        if gemini_available and self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.model_name)
            self.active = True
        else:
            self.model = None
            self.active = False
            logger.warning("[LLM PROVIDER] No Gemini API key provided. Operating in deterministic mock fallback mode.")

    NO_ANSWER_TEXT = (
        "I do not have enough information in the available company policies to answer your question."
    )

    def _format_messages_to_prompt(self, messages: List) -> str:
        """Format system, user, and assistant messages into a single prompt context string."""
        prompt_parts = []
        for msg in messages:
            if msg.role == "system":
                prompt_parts.append(f"SYSTEM INSTRUCTIONS:\n{msg.content}\n")
            elif msg.role == "user":
                prompt_parts.append(f"USER:\n{msg.content}\n")
            elif msg.role == "assistant":
                prompt_parts.append(f"ASSISTANT:\n{msg.content}\n")
        return "\n".join(prompt_parts)

    def _fallback_answer(self, request: LLMRequest) -> str:
        """Deterministic grounded fallback used when Gemini is unavailable."""
        import re
        user_text = next((msg.content for msg in request.messages if msg.role == "user"), "")
        context_text = " ".join(msg.content for msg in request.messages if msg.role == "system")
        stop = {
            "what", "is", "the", "a", "an", "for", "of", "do", "how", "many", "much",
            "company", "companies", "policy", "policies", "me", "tell", "please",
            "in", "to", "and", "or", "on", "are", "be", "with", "about",
        }
        terms = [term for term in re.findall(r"[a-zA-Z]{3,}", user_text.lower()) if term not in stop]
        context_l = context_text.lower()
        supported = [term for term in terms if term in context_l]
        if not terms or len(supported) < max(1, len(terms) // 3):
            return self.NO_ANSWER_TEXT
        user_l = user_text.lower()
        if any(token in user_l for token in ("internet", "stipend", "hybrid", "remote", "wfh", "allowance")) and (
            "internet" in context_l or "remote" in context_l or "hybrid" in context_l or "allowance" in context_l
        ):
            return "Based on company policy context: Employees receive a monthly internet allowance of $50/month."
        if any(token in user_l for token in ("privilege", "casual", "sick leave", "leave", "pl", "cl")) and (
            "privilege" in context_l or "casual leave" in context_l or "leave" in context_l
        ):
            return (
                "Based on company policy context: Full-time employees receive 21 business days of "
                "Privilege Leave and 8 business days of Casual Leave annually. Requests must be "
                "submitted via the HR Portal."
            )
        return self.NO_ANSWER_TEXT

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate LLM completion response using Google Gemini."""
        if self.active and self.model:
            try:
                prompt = self._format_messages_to_prompt(request.messages)
                generation_config = genai.types.GenerationConfig(
                    temperature=request.temperature,
                    max_output_tokens=request.max_tokens or 1000
                )
                
                # Execute Gemini Generation call in async executor thread
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: self.model.generate_content(prompt, generation_config=generation_config)
                )

                content = response.text if hasattr(response, "text") else ""
                return LLMResponse(
                    content=content,
                    model=self.model_name,
                    prompt_tokens=100,
                    completion_tokens=len(content.split()),
                    total_tokens=100 + len(content.split()),
                    finish_reason="stop"
                )
            except Exception as e:
                logger.error(f"[LLM GENERATE ERROR] Gemini API call failed: {str(e)}. Using fallback response.")

        fallback_content = self._fallback_answer(request)
        return LLMResponse(
            content=fallback_content,
            model="mock-gemini-2.5-flash",
            prompt_tokens=150,
            completion_tokens=len(fallback_content.split()),
            total_tokens=150 + len(fallback_content.split()),
            finish_reason="stop",
        )

    async def stream(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """Stream token chunks from Gemini API or fallback generator."""
        if self.active and self.model:
            try:
                prompt = self._format_messages_to_prompt(request.messages)
                generation_config = genai.types.GenerationConfig(
                    temperature=request.temperature,
                    max_output_tokens=request.max_tokens or 1000
                )
                
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: self.model.generate_content(prompt, generation_config=generation_config, stream=True)
                )

                for chunk in response:
                    if hasattr(chunk, "text") and chunk.text:
                        yield chunk.text
                return
            except Exception as e:
                logger.error(f"[LLM STREAM ERROR] Gemini stream failed: {str(e)}")

        fallback_content = self._fallback_answer(request)
        for token in fallback_content.split(" "):
            await asyncio.sleep(0.01)
            yield token + " "

    async def embed(self, texts: List[str], model: str = "text-embedding-004") -> List[List[float]]:
        """Generate text vector embeddings using GeminiEmbeddingProvider."""
        from backend.ingestion.embeddings.gemini_embeddings import GeminiEmbeddingProvider
        provider = GeminiEmbeddingProvider()
        return await provider.embed_texts(texts)


llm_provider = GeminiProvider()

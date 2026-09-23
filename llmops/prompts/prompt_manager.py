"""
Git-managed Prompt Lifecycle Manager tracking versions and metadata.
"""

from typing import Dict, Optional
from pydantic import BaseModel


class PromptVersion(BaseModel):
    """Prompt template specification with lifecycle state."""
    id: str
    version: str
    description: str
    template: str
    status: str = "production"  # draft, testing, approved, production, deprecated
    model_compatibility: str = "gemini-2.5-flash"


class PromptManager:
    """Manages prompt template retrieval, version resolution, and registry."""

    def __init__(self):
        self._prompts: Dict[str, PromptVersion] = {
            "rag_system_prompt": PromptVersion(
                id="rag_system_prompt",
                version="v1.3",
                description="Grounding system prompt enforcing policy-only context and no-hallucination constraint.",
                template=(
                    "You are an official enterprise Employee Knowledge Assistant. "
                    "Answer the user's question accurately based ONLY on the provided company policy context. "
                    "If the information is unavailable in the context, state: "
                    "'I do not have enough information in the available company policies to answer your question.' "
                    "Do NOT invent policy details.\n\nContext:\n{context}"
                ),
                status="production",
                model_compatibility="gemini-2.5-flash",
            )
        }

    def get_prompt(self, prompt_id: str, version: Optional[str] = None) -> PromptVersion:
        """Retrieve approved production prompt version."""
        if prompt_id not in self._prompts:
            raise KeyError(f"Prompt '{prompt_id}' not registered.")
        return self._prompts[prompt_id]


prompt_manager = PromptManager()

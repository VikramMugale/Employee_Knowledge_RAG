"""
ACL Filter builder constructing payload metadata filters for Qdrant and OpenSearch.
"""

from typing import Dict, Any
from backend.auth.models import UserContext, Role
from backend.ingestion.models import ChunkMetadata


class ACLFilterBuilder:
    """
    Constructs database-native payload metadata filters enforcing the security invariant:
    Unauthorized chunks must NEVER enter retrieval candidate pool or LLM context.
    """

    def build_qdrant_acl_filter(self, user_context: UserContext) -> Dict[str, Any]:
        """Construct Qdrant payload filter query dictionary."""
        return {
            "must": [
                {
                    "key": "access_level",
                    "match": {"any": user_context.allowed_access_levels}
                }
            ]
        }

    def build_opensearch_acl_filter(self, user_context: UserContext) -> Dict[str, Any]:
        """Construct OpenSearch terms filter query dictionary."""
        return {
            "terms": {
                "chunk_metadata.access_level.keyword": user_context.allowed_access_levels
            }
        }

    def allows(self, user_context: UserContext, metadata: ChunkMetadata) -> bool:
        """In-memory ACL check used by local fallback indexes."""
        if user_context.role == Role.ADMIN:
            return True
        if metadata.access_level not in set(user_context.allowed_access_levels):
            return False
        if metadata.allowed_roles and user_context.role.value not in metadata.allowed_roles:
            return False
        return True


acl_filter_builder = ACLFilterBuilder()

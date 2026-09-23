"""Persistent conversation history in PostgreSQL when configured."""
from typing import List
from backend.config.logging import logger
from backend.config.settings import settings
from backend.rag.conversation import conversation_memory


async def ensure_conversation(conversation_id: str, user_id: str, title: str) -> str:
    if not conversation_id or not settings.uses_postgres():
        return conversation_id
    try:
        from backend.db.session import AsyncSessionLocal
        from backend.db.models.entities import ConversationEntity, UserEntity
        if AsyncSessionLocal is None:
            return conversation_id
        async with AsyncSessionLocal() as session:
            if await session.get(UserEntity, user_id) is None:
                session.add(UserEntity(id=user_id, email=f"{user_id}@local", full_name=user_id))
            if await session.get(ConversationEntity, conversation_id) is None:
                session.add(ConversationEntity(id=conversation_id, user_id=user_id, title=(title or "Conversation")[:255]))
            await session.commit()
    except Exception as exc:
        logger.warning("[CONVERSATION] persist ensure failed: %s", exc)
    return conversation_id


async def append_message(conversation_id: str, role: str, content: str, trace_id: str = None) -> None:
    if role == "user":
        conversation_memory.add_user_turn(conversation_id, content)
    if not settings.uses_postgres() or not conversation_id:
        return
    try:
        from backend.db.session import AsyncSessionLocal
        from backend.db.models.entities import MessageEntity
        if AsyncSessionLocal is None:
            return
        async with AsyncSessionLocal() as session:
            session.add(MessageEntity(conversation_id=conversation_id, role=role, content=content, trace_id=trace_id))
            await session.commit()
    except Exception as exc:
        logger.warning("[CONVERSATION] persist message failed: %s", exc)


async def recent_user_turns(conversation_id: str, limit: int = 8) -> List[str]:
    if settings.uses_postgres() and conversation_id:
        try:
            from sqlalchemy import select
            from backend.db.session import AsyncSessionLocal
            from backend.db.models.entities import MessageEntity
            if AsyncSessionLocal is not None:
                async with AsyncSessionLocal() as session:
                    result = await session.execute(
                        select(MessageEntity)
                        .where(MessageEntity.conversation_id == conversation_id)
                        .where(MessageEntity.role == "user")
                        .order_by(MessageEntity.created_at.desc())
                        .limit(limit)
                    )
                    rows = list(reversed(result.scalars().all()))
                    if rows:
                        return [row.content for row in rows]
        except Exception as exc:
            logger.warning("[CONVERSATION] load history failed: %s", exc)
    return conversation_memory.recent_user_turns(conversation_id)

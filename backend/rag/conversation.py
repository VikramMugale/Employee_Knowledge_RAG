"""
In-process conversation memory.

PostgreSQL remains the system of record when configured. This store keeps the
last N turns available for query rewrite without introducing Redis.
"""

from collections import defaultdict, deque
from typing import Deque, Dict, List


class ConversationMemory:
    def __init__(self, max_turns: int = 8):
        self.max_turns = max_turns
        self._turns: Dict[str, Deque[str]] = defaultdict(lambda: deque(maxlen=self.max_turns))

    def add_user_turn(self, conversation_id: str, text: str) -> None:
        if not conversation_id:
            return
        self._turns[conversation_id].append(text)

    def recent_user_turns(self, conversation_id: str) -> List[str]:
        if not conversation_id:
            return []
        return list(self._turns.get(conversation_id, []))


conversation_memory = ConversationMemory()

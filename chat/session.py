"""
Chat session memory management.
Maintains per-session conversation history with context window management.
"""

import logging
import time
from typing import List, Dict, Optional
from collections import OrderedDict

logger = logging.getLogger(__name__)

MAX_HISTORY_MESSAGES = 20  # Keep last N messages per session
MAX_SESSIONS = 100         # Max concurrent sessions


class ChatSession:
    """Manages a single chat session's conversation history."""

    def __init__(self, session_id: str, domain_name: str):
        self.session_id = session_id
        self.domain_name = domain_name
        self.messages: List[Dict] = []
        self.created_at = time.time()
        self.last_active = time.time()

    def add_message(self, role: str, content: str):
        """Add a message to the conversation history."""
        self.messages.append({"role": role, "content": content})
        self.last_active = time.time()

        # Trim if exceeding max
        if len(self.messages) > MAX_HISTORY_MESSAGES:
            # Keep system message if present, then trim oldest
            system_msgs = [m for m in self.messages if m["role"] == "system"]
            other_msgs = [m for m in self.messages if m["role"] != "system"]
            keep = other_msgs[-(MAX_HISTORY_MESSAGES - len(system_msgs)):]
            self.messages = system_msgs + keep

    def get_messages(self) -> List[Dict]:
        """Get the full conversation history."""
        return self.messages.copy()

    def clear(self):
        """Clear the conversation history."""
        self.messages = []


class SessionManager:
    """Manages multiple chat sessions."""

    def __init__(self):
        self._sessions: OrderedDict[str, ChatSession] = OrderedDict()

    def get_or_create(self, session_id: str, domain_name: str) -> ChatSession:
        """Get existing session or create a new one."""
        if session_id not in self._sessions:
            # Evict oldest if at capacity
            while len(self._sessions) >= MAX_SESSIONS:
                self._sessions.popitem(last=False)

            self._sessions[session_id] = ChatSession(session_id, domain_name)

        session = self._sessions[session_id]
        session.last_active = time.time()
        return session

    def remove(self, session_id: str):
        """Remove a session."""
        self._sessions.pop(session_id, None)

    def get(self, session_id: str) -> Optional[ChatSession]:
        """Get a session by ID."""
        return self._sessions.get(session_id)


# Global session manager
session_manager = SessionManager()

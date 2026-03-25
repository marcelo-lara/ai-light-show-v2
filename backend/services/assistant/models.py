from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class ActiveRequest:
    request_id: str
    client_id: str
    assistant_id: str
    prompt: str


@dataclass
class PendingAction:
    request_id: str
    client_id: str
    assistant_id: str
    prompt: str
    action_id: str
    tool_name: str
    arguments: Dict[str, Any]
    title: str
    summary: str

@dataclass
class ConversationTurn:
    role: str
    content: str
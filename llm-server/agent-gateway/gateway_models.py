from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ChatRequest(BaseModel):
    messages: List[Dict[str, Any]]
    model: Optional[str] = "local"
    temperature: Optional[float] = 0.2
    tool_choice: Optional[Any] = "auto"
    stream: Optional[bool] = False
    assistant_id: Optional[str] = "generic"
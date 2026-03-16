from __future__ import annotations

from typing import Any, Dict, List


def build_chasers_payload(manager) -> List[Dict[str, Any]]:
    return manager.state_manager.get_chasers()

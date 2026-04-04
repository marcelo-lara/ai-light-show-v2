from __future__ import annotations

from typing import Any, Callable

ProgressCallback = Callable[[dict[str, Any]], None]


def emit_stage(
    progress_callback: ProgressCallback | None,
    task_type: str,
    stage: str,
    step_current: int,
    step_total: int,
    part_name: str | None = None,
) -> None:
    print(f"{task_type} - {stage} ({step_current}/{step_total})")       
    if progress_callback is None:
        return
    event: dict[str, Any] = {
        "task_type": task_type,
        "stage": stage,
        "step_current": step_current,
        "step_total": step_total,
        "message": f"{task_type} [{step_current}/{step_total}] {stage}",
    }
    if part_name is not None:
        event["part_name"] = part_name
    progress_callback(event)
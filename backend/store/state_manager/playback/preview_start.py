# pyright: reportAttributeAccessIssue=false

import asyncio
import contextlib
from typing import Any, Dict, Optional
from uuid import uuid4


class StatePlaybackPreviewStartMixin:
    async def start_preview_effect(
        self,
        fixture_id: str,
        effect: str,
        duration: float,
        data: Optional[Dict[str, Any]],
        request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        cancel_task: Optional[asyncio.Task] = None

        async with self.lock:
            if self.is_playing:
                return {"ok": False, "reason": "playback_active"}

            fixture = self._get_fixture(str(fixture_id or "").strip())
            if not fixture:
                return {"ok": False, "reason": "fixture_not_found"}

            normalized_effect = str(effect or "").strip().lower()
            if normalized_effect not in self._fixture_supported_effects(fixture):
                return {"ok": False, "reason": "effect_not_supported"}

            preview_duration = float(duration or 0.0)
            if preview_duration <= 0:
                return {"ok": False, "reason": "invalid_duration"}

            rid = str(request_id or uuid4())
            if self.preview_task:
                cancel_task = self.preview_task

            base_universe = bytearray(self.editor_universe)
            self.preview_canvas = self._render_preview_canvas(
                fixture=fixture,
                effect=normalized_effect,
                duration=preview_duration,
                data=data or {},
                base_universe=base_universe,
            )
            self.preview_request_id = rid
            self.preview_fixture_id = fixture.id
            self.preview_effect = normalized_effect
            self.preview_duration = preview_duration
            self.preview_active = True
            self.output_universe[:] = self.preview_canvas.frame_view(0)
            self.preview_task = asyncio.create_task(self._run_preview(rid))

        if cancel_task:
            cancel_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await cancel_task

        return {
            "ok": True,
            "requestId": rid,
            "fixtureId": fixture_id,
            "effect": normalized_effect,
            "duration": float(preview_duration),
        }

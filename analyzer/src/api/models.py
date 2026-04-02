from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class QueueItemCreate(BaseModel):
    task_type: str
    params: dict[str, Any]


class PlaybackLockUpdate(BaseModel):
    locked: bool


class FullArtifactPlaylistRequest(BaseModel):
    song_path: str
    meta_path: str = "/app/meta"
    device: str | None = None


class QueueFullArtifactPlaylistRequest(FullArtifactPlaylistRequest):
    activate: bool = True
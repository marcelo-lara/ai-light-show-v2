from __future__ import annotations

from typing import Any, Dict, List, Optional

from .config import Settings
from .errors import QueryError
from .index import MetadataIndexStore

try:
    from fastmcp import FastMCP
except Exception:  # pragma: no cover
    from mcp.server.fastmcp import FastMCP  # type: ignore


def create_server(settings: Settings) -> FastMCP:
    store = MetadataIndexStore(
        meta_root=settings.meta_root,
        max_raw_points=settings.max_raw_points,
        default_max_points=settings.default_max_points,
    )

    mcp = FastMCP("song-metadata-mcp")

    @mcp.tool()
    def list_songs() -> Dict[str, Any]:
        try:
            songs = store.list_songs()
            return {"ok": True, "data": {"songs": songs, "count": len(songs)}}
        except QueryError as error:
            return store.to_error(error)

    @mcp.tool()
    def list_features(song: str) -> Dict[str, Any]:
        try:
            return store.list_features(song=song)
        except QueryError as error:
            return store.to_error(error)

    @mcp.tool()
    def get_song_overview(song: str) -> Dict[str, Any]:
        try:
            return store.get_song_overview(song=song)
        except QueryError as error:
            return store.to_error(error)

    @mcp.tool()
    def query_feature(
        song: str,
        feature: str,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        include_raw: bool = False,
        mode: str = "summary",
        max_points: Optional[int] = None,
        time_tolerance_ms: float = 0.0,
    ) -> Dict[str, Any]:
        try:
            return store.query_feature(
                song=song,
                feature=feature,
                start_time=start_time,
                end_time=end_time,
                include_raw=include_raw,
                mode=mode,
                max_points=max_points,
                time_tolerance_ms=time_tolerance_ms,
            )
        except QueryError as error:
            return store.to_error(error)

    @mcp.tool()
    def query_window(
        song: str,
        start_time: float,
        end_time: float,
        features: List[str],
        include_raw: bool = False,
        mode: str = "summary",
        max_points: Optional[int] = None,
        time_tolerance_ms: float = 0.0,
    ) -> Dict[str, Any]:
        try:
            return store.query_window(
                song=song,
                start_time=start_time,
                end_time=end_time,
                features=features,
                include_raw=include_raw,
                mode=mode,
                max_points=max_points,
                time_tolerance_ms=time_tolerance_ms,
            )
        except QueryError as error:
            return store.to_error(error)

    return mcp

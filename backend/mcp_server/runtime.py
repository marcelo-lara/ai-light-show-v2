from __future__ import annotations


class BackendMcpRuntime:
    def __init__(self) -> None:
        self.ws_manager = None
        self.song_service = None

    def attach(self, ws_manager, song_service) -> None:
        self.ws_manager = ws_manager
        self.song_service = song_service

    def clear(self) -> None:
        self.ws_manager = None
        self.song_service = None

    def require_ws_manager(self):
        if self.ws_manager is None:
            raise RuntimeError("backend_mcp_not_ready")
        return self.ws_manager

    def require_song_service(self):
        if self.song_service is None:
            raise RuntimeError("backend_mcp_not_ready")
        return self.song_service
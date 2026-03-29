from __future__ import annotations

try:
    from fastmcp import FastMCP
except Exception:  # pragma: no cover
    from mcp.server.fastmcp import FastMCP  # type: ignore

from .cues import register_cue_tools
from .fixtures import register_fixtures_tools
from .metadata import register_metadata_tools
from .songs import register_songs_tools
from .transport import register_transport_tools
from .effects import register_effects_tools
from .pois import register_pois_tools

def create_backend_mcp(runtime) -> FastMCP:
    mcp = FastMCP("ai-light-backend")
    register_songs_tools(mcp, runtime)
    register_fixtures_tools(mcp, runtime)
    register_cue_tools(mcp, runtime)
    register_metadata_tools(mcp, runtime)
    register_transport_tools(mcp, runtime)
    register_effects_tools(mcp, runtime)
    register_pois_tools(mcp, runtime)
    return mcp
    return mcp
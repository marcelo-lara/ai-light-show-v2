from mcp.server.fastmcp import FastMCP
from models.fixtures.effects.registry import REGISTRY

from .responses import ok

def register_effects_tools(mcp: FastMCP, runtime):
    @mcp.tool()
    def list_effects() -> dict:
        """
        Retrieves the global effect registry.
        
        Returns a dictionary where each key is an effect ID (e.g. 'fade_in', 'color_fade', 'move_to')
        and the value contains its metadata including 'name', 'description', 'tags', and the 'schema'
        describing its required JSON data structure.
        """
        effects = REGISTRY.serialize_all()
        return ok({"effects": effects, "count": len(effects)})

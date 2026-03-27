from mcp.server.fastmcp import FastMCP
from models.fixtures.effects.registry import REGISTRY

def register_effects_tools(mcp: FastMCP, runtime):
    @mcp.tool()
    def list_effects() -> dict:
        """
        Retrieves the global effect registry.
        
        Returns a dictionary where each key is an effect ID (e.g. 'fade_in', 'color_fade', 'move_to')
        and the value contains its 'name', 'description', and the 'schema' describing its required JSON data structure.
        """
        effects = {}
        for effect_id, eff in REGISTRY._effects.items():
            effects[effect_id] = {
                "name": eff.name,
                "description": eff.description,
                "schema": eff.schema,
            }
        return effects

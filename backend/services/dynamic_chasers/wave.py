import math
from typing import Dict, List, Any
from .utils import hex_to_rgb, get_envelope

def dynamic_wave_generator(params: Dict[str, Any]) -> List[Dict]:
    """
    Generates an organic, sine-modulated wave across fixtures.
    Supports: base_color, accent_color, speed, and fade envelopes.
    """
    fixtures = params.get("fixtures", ["parcan_pl", "parcan_l", "parcan_r", "parcan_pr"])
    base_rgb = hex_to_rgb(params.get("base_color", "#000814"))
    accent_rgb = hex_to_rgb(params.get("accent_color", "#00F5FF"))
    total_beats = params.get("duration_beats", 4.0)
    resolution = params.get("step_size", 0.05)  # 20 steps per beat for smoothness
    speed = params.get("speed", 1.0)
    fade_in = params.get("fade_in_beats", 1.0)
    fade_out = params.get("fade_out_beats", 1.0)
    
    effects = []
    num_fixtures = len(fixtures)
    
    curr_beat = 0.0
    while curr_beat < total_beats:
        envelope = get_envelope(curr_beat, total_beats, fade_in, fade_out)
        
        for i, fixture_id in enumerate(fixtures):
            # Math: Spatial offset (based on fixture index) + Time offset (based on beat)
            spatial_phase = (i / num_fixtures) * 2 * math.pi
            time_phase = curr_beat * speed * math.pi
            
            modulation = (math.sin(spatial_phase - time_phase) + 1) / 2
            
            # Interpolate colors and apply intensity envelope
            r = int((base_rgb[0] + (accent_rgb[0] - base_rgb[0]) * modulation) * envelope)
            g = int((base_rgb[1] + (accent_rgb[1] - base_rgb[1]) * modulation) * envelope)
            b = int((base_rgb[2] + (accent_rgb[2] - base_rgb[2]) * modulation) * envelope)
            
            effects.append({
                "beat": round(curr_beat, 3),
                "fixture_id": fixture_id,
                "effect": "set_channels",
                "duration": resolution,
                "data": {"red": r, "green": g, "blue": b}
            })
        
        curr_beat += resolution
        
    return effects
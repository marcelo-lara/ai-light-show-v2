def hex_to_rgb(hex_str: str):
    """Converts hex color strings (including shorthand) to RGB list."""
    hex_str = hex_str.lstrip('#')
    if len(hex_str) == 3:
        hex_str = "".join([c*2 for c in hex_str])
    return [int(hex_str[i:i+2], 16) for i in (0, 2, 4)]

def get_envelope(curr_beat: float, total_beats: float, fade_in: float, fade_out: float) -> float:
    """Calculates a linear intensity envelope (0.0 to 1.0) for smooth transitions."""
    if curr_beat < fade_in and fade_in > 0:
        return curr_beat / fade_in
    if curr_beat > (total_beats - fade_out) and fade_out > 0:
        return max(0.0, (total_beats - curr_beat) / fade_out)
    return 1.0
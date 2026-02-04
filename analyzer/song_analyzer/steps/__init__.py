# Analysis pipeline steps

def get_available_steps() -> list[str]:
    """Get list of available analysis steps in execution order."""
    return [
        "00_ingest",
        "10_stems",
        "20_beats",
        "30_energy",
        "40_drums",
        "50_vocals",
        "60_sections",
        "70_patterns",
        "80_show_plan",
    ]
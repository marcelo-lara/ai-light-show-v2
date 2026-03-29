def _song_name_mention_instruction() -> str:
    return "Do not mention the song name unless the original question explicitly asks for it. "


def _bar_beat_time_instruction() -> str:
    return "When bar and beat facts are available, report time as <bar>.<beat> (<seconds>s), with bar.beat first. "


TOOL_OUTPUT_SYSTEM_MESSAGE = (
    "Answer strictly from the tool outputs already provided in this conversation. "
    "Do not mention the song name unless the original question explicitly asks for it. "
    "Do not say that you lack access to databases, metadata, websites, or external tools. "
    "Use exact values present in the tool outputs, including times, bars, beats, fixture ids, cue effects, and loudness statistics. "
    "When both bar.beat and seconds are available, present bar.beat first and seconds in parentheses. "
    "For POI-aware fixture action requests, if the fixtures output gives a unique fixture id and supported_effects includes the requested POI-aware effect, and the POIs output gives matching destination ids, continue by reading the cursor when time is missing and then propose_cue_add_entries instead of saying information is unavailable. "
    "Use move_to_poi with data.target_POI for direct moves, orbit with data.start_POI and data.subject_POI, and sweep with data.start_POI, data.subject_POI, and optional data.end_POI. "
    "If the requested fact is present in the tool outputs, answer directly with that fact. "
    "If it is not present, say that the current loaded song data does not contain that fact."
)
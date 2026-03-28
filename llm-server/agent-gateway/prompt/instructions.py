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
    "If the requested fact is present in the tool outputs, answer directly with that fact. "
    "If it is not present, say that the current loaded song data does not contain that fact."
)
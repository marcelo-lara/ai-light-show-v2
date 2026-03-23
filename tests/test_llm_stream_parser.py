import json

from api.intents.llm.stream_parser import parse_stream_line


def test_parse_stream_line_extracts_chunk():
    line = "data: " + json.dumps({"choices": [{"delta": {"content": "Hello"}, "finish_reason": None}]})

    event = parse_stream_line(line)

    assert event == {"type": "content", "content": "Hello", "done": False}


def test_parse_stream_line_extracts_status():
    event = parse_stream_line('data: {"type":"status","status":"Looking up song sections"}')

    assert event == {"type": "status", "status": "Looking up song sections"}


def test_parse_stream_line_detects_done_sentinel():
    event = parse_stream_line("data: [DONE]")

    assert event == {"type": "done"}
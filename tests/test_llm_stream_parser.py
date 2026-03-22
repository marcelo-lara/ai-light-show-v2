import json

from api.intents.llm.stream_parser import parse_stream_line


def test_parse_stream_line_extracts_chunk():
    line = "data: " + json.dumps({"choices": [{"delta": {"content": "Hello"}, "finish_reason": None}]})

    chunk, done = parse_stream_line(line)

    assert chunk == "Hello"
    assert done is False


def test_parse_stream_line_detects_done_sentinel():
    chunk, done = parse_stream_line("data: [DONE]")

    assert chunk == ""
    assert done is True
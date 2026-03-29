import os

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://llm-server:8080")
MCP_BASE_URL = os.getenv("MCP_BASE_URL", "http://backend:5001/mcp")

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "mcp_read_sections",
            "description": "Read the song sections with exact names, time ranges, and resolved start/end bars and beats.",
            "parameters": {"type": "object", "properties": {"song_id": {"type": "string"}}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "mcp_find_section",
            "description": "Find one exact section by name for the current song. Use this for questions like 'where does the verse start?' or 'when does the chorus end?'.",
            "parameters": {"type": "object", "properties": {"section_name": {"type": "string"}}, "required": ["section_name"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "mcp_read_section_analysis",
            "description": "Read grounded section-analysis summaries including mix loudness stats, stem-supported events from bass, drums, and vocals, and harmonic patterns for metadata drafting.",
            "parameters": {
                "type": "object",
                "properties": {"song_id": {"type": "string"}, "section_name": {"type": "string"}},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "mcp_read_beats",
            "description": "Read beat entries with time, bar, and beat values for an optional time window.",
            "parameters": {
                "type": "object",
                "properties": {"song_id": {"type": "string"}, "start_time": {"type": "number"}, "end_time": {"type": "number"}},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "mcp_read_bar_beats",
            "description": "Read beat entries by musical position using start/end bars and beats instead of seconds.",
            "parameters": {
                "type": "object",
                "properties": {
                    "song_id": {"type": "string"},
                    "start_bar": {"type": "integer"},
                    "start_beat": {"type": "integer"},
                    "end_bar": {"type": "integer"},
                    "end_beat": {"type": "integer"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "mcp_find_bar_beat",
            "description": "Find one exact beat row for a specific bar and beat and return its exact time and chord context.",
            "parameters": {
                "type": "object",
                "properties": {"song_id": {"type": "string"}, "bar": {"type": "integer"}, "beat": {"type": "integer"}},
                "required": ["bar", "beat"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "mcp_find_chord",
            "description": "Find an exact chord occurrence by label and return its time, bar, and beat.",
            "parameters": {
                "type": "object",
                "properties": {"song_id": {"type": "string"}, "chord": {"type": "string"}, "occurrence": {"type": "integer"}},
                "required": ["chord"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "mcp_read_chords",
            "description": "Read chord changes for the current song or a time window.",
            "parameters": {
                "type": "object",
                "properties": {"song_id": {"type": "string"}, "start_time": {"type": "number"}, "end_time": {"type": "number"}},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "mcp_read_cue_window",
            "description": "Read cue entries in a specific time window.",
            "parameters": {"type": "object", "properties": {"start_time": {"type": "number"}, "end_time": {"type": "number"}}, "required": ["start_time", "end_time"]},
        },
    },
    {"type": "function", "function": {"name": "mcp_read_fixtures", "description": "Read the fixture list including ids, names, types, capabilities, positions, and supported_effects. Use this to resolve phrases like 'el-150 moving head' to exact fixture ids and to confirm whether a fixture supports move_to_poi.", "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {"name": "mcp_read_pois", "description": "Read the available POIs and their ids. Use this when a request mentions named stage locations like piano, table, or center.", "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {"name": "mcp_read_chasers", "description": "Read the available chaser definitions.", "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {"name": "mcp_read_cursor", "description": "Read the current transport cursor time, section, and nearest bar.beat.", "parameters": {"type": "object", "properties": {}, "required": []}}},
    {
        "type": "function",
        "function": {
            "name": "mcp_read_loudness",
            "description": "Read loudness statistics for a time window or section.",
            "parameters": {
                "type": "object",
                "properties": {"song_id": {"type": "string"}, "section": {"type": "string"}, "start_time": {"type": "number"}, "end_time": {"type": "number"}},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "mcp_read_effects",
            "description": "Read effect metadata including description, controlled tags, and schema. Use this before suggesting which effect fits an intent like spike, drop, sustain, tension, or soft motion.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "propose_cue_clear_range",
            "description": "Propose clearing cue entries in a specific time range. Use for destructive cue sheet edits that need confirmation.",
            "parameters": {"type": "object", "properties": {"start_time": {"type": "number"}, "end_time": {"type": "number"}}, "required": ["start_time", "end_time"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "propose_cue_add_entries",
            "description": "Propose adding one or more effect cue entries. Use for cue edits that need confirmation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "entries": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "time": {"type": "number"},
                                "fixture_id": {"type": "string"},
                                "effect": {"type": "string"},
                                "duration": {"type": "number"},
                                "data": {"type": "object"},
                            },
                            "required": ["time", "fixture_id", "effect", "duration", "data"],
                        },
                    }
                },
                "required": ["entries"],
            },
        },
    },
    {"type": "function", "function": {"name": "propose_cue_clear_all", "description": "Propose clearing every cue entry from the current cue sheet. Use for destructive whole-sheet clears that need confirmation.", "parameters": {"type": "object", "properties": {}, "required": []}}},
    {
        "type": "function",
        "function": {
            "name": "propose_chaser_apply",
            "description": "Propose adding a chaser cue entry starting at a time with repetitions. Use for cue changes that need confirmation.",
            "parameters": {
                "type": "object",
                "properties": {"chaser_id": {"type": "string"}, "start_time": {"type": "number"}, "repetitions": {"type": "integer"}},
                "required": ["chaser_id", "start_time", "repetitions"],
            },
        },
    },
]

MCP_TOOL_MAP = {
    "mcp_read_sections": "metadata_get_sections",
    "mcp_find_section": "metadata_find_section",
    "mcp_read_section_analysis": "metadata_get_section_analysis",
    "mcp_read_beats": "metadata_get_beats",
    "mcp_read_bar_beats": "metadata_get_bar_beats",
    "mcp_find_bar_beat": "metadata_find_bar_beat",
    "mcp_find_chord": "metadata_find_chord",
    "mcp_read_chords": "metadata_get_chords",
    "mcp_read_cue_window": "cues_get_window",
    "mcp_read_fixtures": "fixtures_list",
    "mcp_read_pois": "pois_list",
    "mcp_read_chasers": "chasers_list",
    "mcp_read_cursor": "transport_get_cursor",
    "mcp_read_loudness": "metadata_get_loudness",
    "mcp_read_effects": "list_effects",
}

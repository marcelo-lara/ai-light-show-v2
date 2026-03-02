# MCP Module (LLM Guide)

Model Context Protocol services for AI Light Show.

## Scope

This folder contains MCP servers that expose project data to LLM agents through tool APIs.

Current service:

- `song_metadata/`: read-only metadata query MCP server.

## song_metadata service

Transport and endpoint model:

- Transport: `sse`
- Stream endpoint: `/sse`
- JSON-RPC messages endpoint: `/messages/?session_id=...`

Available tools:

- `list_songs()`
- `list_features(song)`
- `get_song_overview(song)`
- `query_feature(...)`
- `query_window(...)`

## Data source contract

- Service reads from metadata root (`/app/meta` in Docker).
- Expected layout aligns with `analyzer/meta/<song>/...` outputs.
- Service is read-only and should not mutate metadata files.

## Development

```bash
cd mcp/song_metadata
pip install -r requirements.txt
python -m song_metadata_mcp.main
```

In Compose, service is published on host `8089`.

## LLM contributor checklist

1. Keep tool names stable; coordinate any rename with gateway mappings.
2. Preserve SSE + session behavior for compatibility with agent-gateway.
3. Keep responses structured and deterministic (`ok/data` or `ok/error`).
4. Add/adjust tests under `mcp/song_metadata/tests/` for behavior changes.

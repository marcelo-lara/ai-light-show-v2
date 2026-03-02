# Song Metadata MCP Service (LLM Guide)

Read-only MCP server for querying analyzer metadata slices from `analyzer/meta`.

## Purpose

- Provide authoritative song timing/feature queries to LLM tool callers.
- Keep analysis access read-only and deterministic.

## Transport and protocol

- Transport: `sse`
- SSE stream endpoint: `/sse`
- Session messages endpoint: `/messages/?session_id=...`

### Important session rule

Clients must keep the same SSE stream open while posting JSON-RPC calls to the session messages endpoint. Opening `/sse`, closing it, then posting messages causes session invalidation.

## Tools

- `list_songs()`
- `list_features(song)`
- `get_song_overview(song)`
- `query_feature(song, feature, start_time?, end_time?, include_raw=false, mode="summary", max_points?, time_tolerance_ms=0)`
- `query_window(song, start_time, end_time, features, include_raw=false, mode="summary", max_points?, time_tolerance_ms=0)`

## Response envelope

- Success: `{ "ok": true, "data": { ... } }`
- Error: `{ "ok": false, "error": { "code", "message", "details?" } }`

## Query modes

- `summary` (default): returns summary, optional decimated raw payload.
- `exact`: returns unmodified raw payload (subject to strict cap).

## Configuration

- `SONG_METADATA_MCP_META_ROOT` (default: `/app/meta`)
- `SONG_METADATA_MCP_HOST` (default: `0.0.0.0`)
- `SONG_METADATA_MCP_PORT` (default: `8089`)
- `SONG_METADATA_MCP_TRANSPORT` (default: `sse`)
- `SONG_METADATA_MCP_MAX_RAW_POINTS` (default: `20000`)
- `SONG_METADATA_MCP_DEFAULT_MAX_POINTS` (default: `5000`)

## Run locally

```bash
cd mcp/song_metadata
pip install -r requirements.txt
python -m song_metadata_mcp.main
```

## Docker Compose notes

- Read-only mount: `./analyzer/meta:/app/meta:ro`
- Published port: `8089:8089`
- Healthcheck should be TCP-level (`127.0.0.1:8089`), not `/sse`

## Debugging quick checks

```bash
curl -N http://localhost:8089/sse
```

You should see an `event: endpoint` with `session_id`.

## LLM contributor checklist

1. Keep tool names and signatures stable.
2. Keep server read-only over metadata files.
3. Preserve deterministic response shape.
4. Add/update tests in `mcp/song_metadata/tests/` when query behavior changes.

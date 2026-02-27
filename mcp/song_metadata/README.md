# Song Metadata MCP Service

Read-only MCP server for querying song metadata slices from `analyzer/meta`.

## Tools

- `list_songs()`
- `list_features(song)`
- `get_song_overview(song)`
- `query_feature(song, feature, start_time?, end_time?, include_raw=false, mode="summary", max_points?, time_tolerance_ms=0)`
- `query_window(song, start_time, end_time, features, include_raw=false, mode="summary", max_points?, time_tolerance_ms=0)`

All tools return a standard envelope:

- Success: `{ "ok": true, "data": { ... } }`
- Error: `{ "ok": false, "error": { "code", "message", "details?" } }`

## Modes

- `summary` (default): summary stats only unless `include_raw=true`. Raw payload is decimated.
- `exact`: when `include_raw=true`, returns unmodified raw points and enforces strict payload cap.

## Environment

- `SONG_METADATA_MCP_META_ROOT` (default: `/app/meta`)
- `SONG_METADATA_MCP_HOST` (default: `0.0.0.0`)
- `SONG_METADATA_MCP_PORT` (default: `8081`)
- `SONG_METADATA_MCP_TRANSPORT` (default: `sse`)
- `SONG_METADATA_MCP_MAX_RAW_POINTS` (default: `20000`)
- `SONG_METADATA_MCP_DEFAULT_MAX_POINTS` (default: `5000`)

## Docker Compose

The project-level `docker-compose.yml` defines service `song-metadata-mcp` with:

- read-only mount `./analyzer/meta:/app/meta:ro`
- internal-only networking (no host port publishing)
- healthcheck on `http://127.0.0.1:8081/sse`

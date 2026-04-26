# AI Light Show v2 — Architecture

## Start here for LLMs

Use these module guides first, then drill into architecture detail docs.

- Project overview: [../README.md](../README.md)
- Frontend module: [../frontend/README.md](../frontend/README.md)
- Backend module: [../backend/README.md](../backend/README.md)
- Backend implementation contract: [architecture/backend_llm_reference.md](architecture/backend_llm_reference.md)
- Backend cues schema: [architecture/backend_cues_schema.md](architecture/backend_cues_schema.md)
- Backend chasers schema: [architecture/backend_chasers_schema.md](architecture/backend_chasers_schema.md)
- LLM server + gateway: [../llm-server/README.md](../llm-server/README.md)
- UI docs + LoFi index: [ui/README.md](ui/README.md)
- Tests module: [../tests/README.md](../tests/README.md)

AI Light Show v2 is split into six primary modules:

- Frontend: strictly a "dumb client" mapping user intents to websocket payloads.
- Backend: FastAPI + asyncio WebSocket server, DMX state/canvas engine, Art-Net sender.
- Data: canonical song audio, generated metadata, and analysis artifacts under `data/`.
- Backend-mounted MCP tool surface: live song, cue, fixture, and metadata tools exposed at `/mcp`.
- LLM agent gateway: OpenAI-compatible wrapper that maps tool calls to MCP JSON-RPC.
- Tests: backend metadata, protocol, and regression coverage.

## How the modules interact

### Canonical runtime flow

1. Frontend sends `hello` and receives backend-authoritative `snapshot` + `patch` updates over `/ws`.
2. Frontend emits only `intent` payloads; backend applies all domain logic and broadcasts state changes.
3. Backend selects nearest precomputed DMX canvas frame and updates Art-Net output.
4. Preview requests (`fixture.preview_effect`) render temporary in-memory output only (no persistence).
5. Song audio lives under `data/songs`, generated metadata under `data/output`, and detailed artifacts under `data/artifacts`; Docker mounts them at `/app/songs`, `/app/meta`, and `/data`.
6. Backend exposes mounted MCP tools and the agent gateway forwards LLM tool calls.

Song audio files live under `data/songs` locally and are mounted into the backend container at `/app/songs`.

### Real-time playback loop

1. Browser-owned player controls real audio playback and local timecode progression.
2. Client sends transport `intent` actions (`transport.play|pause|stop|jump_to_time`) and syncs current timecode to backend while playing.
3. Backend maps time → frame index and selects the nearest precomputed DMX canvas frame.
4. Backend Art-Net service emits `output_universe` continuously.

### Authoring loop (paused)

1. Client sends `{type:"intent", name:"fixture.set_values", payload:{...}}`.
2. Backend updates fixture/editor-output state according to current playback/preview status.
3. Backend broadcasts `patch` updates.

### Preview loop (paused only)

1. Client sends `{type:"intent", name:"fixture.preview_effect", payload:{...}}`.
2. Backend rejects if playback is active.
3. If accepted, backend renders a temporary in-memory preview canvas and drives Art-Net from it.
4. Backend emits `event` + `patch` updates; preview is never persisted to cues/files.

### Metadata loop

1. Song metadata is read from `data/output/<song>/info.json` and companion files.
2. Backend resolves artifact paths declared there, including manifests under `data/artifacts/<song>/...`.

### Meta source (Docker)

- In Docker, backend reads song metadata from `/app/meta` (mounted from `data/output`).
- Artifact paths declared under `/data/output/...`, `/data/artifacts/...`, and `/data/songs/...` resolve through the shared `/data` mount.

## Module docs

- Frontend module guide: [../frontend/README.md](../frontend/README.md)
- Backend module guide: [../backend/README.md](../backend/README.md)
- Backend implementation contract: [architecture/backend_llm_reference.md](architecture/backend_llm_reference.md)
- LLM stack guide: [../llm-server/README.md](../llm-server/README.md)
- Test module guide: [../tests/README.md](../tests/README.md)
- Deep architecture docs: [backend architecture](architecture/backend.md)

## WebSocket protocol (canonical)

Backend → Client:

- `snapshot`: `{ type:"snapshot", seq, state }`
- `patch`: `{ type:"patch", seq, changes:[{path, value}] }`
- `event`: `{ type:"event", level, message, data? }`

Client → Backend:

- `hello`
- `intent`: `{ type:"intent", req_id, name, payload }`

## Appendix: rendered sequence artifacts

In xLights ecosystems, common file types:

| Extension | Type | Content |
| --- | --- | --- |
| `.fseq` | Binary (rendered) | Raw byte arrays for Art-Net/DMX output |
| `.xsq` | XML (source) | Sequence timeline and effect settings |
| `.xml` | XML (config) | Controller and prop layout settings |
| `.eseq` | Binary (effect) | Byte arrays for a single model/prop |

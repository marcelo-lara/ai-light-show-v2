# LLM Tuning Tool

Standalone live runner for sending one prompt at a time to the backend websocket and saving the full interaction transcript for later inspection.

## What it does

- Reads one non-empty line per prompt from `user-requests.txt`.
- Accepts a single prompt directly from the CLI with `--prompt`.
- Opens a fresh websocket connection to the live backend for each prompt.
- Waits for the initial `snapshot` before sending anything.
- Sends `llm.send_prompt` with `payload.prompt`.
- Records raw inbound and outbound websocket messages in order.
- Reconstructs the final answer from streamed `llm_delta` events.
- Auto-confirms `llm_action_proposed` events and continues until `llm_done`, `llm_error`, or timeout.
- Writes one JSON session log per run under `logs/`.

## Runtime assumptions

- Backend websocket is available at `ws://localhost:5001/ws`.
- The Docker stack is already running.
- The project Python environment is `ai-light`.

Bring up the stack if needed:

```bash
docker compose up -d
```

## Run

```bash
/home/darkangel/.pyenv/versions/ai-light/bin/python tests/llm-tuning-tool/llm-tuning-tool.py
```

Run a subset:

```bash
/home/darkangel/.pyenv/versions/ai-light/bin/python tests/llm-tuning-tool/llm-tuning-tool.py --limit 3
```

Run a custom prompt file:

```bash
/home/darkangel/.pyenv/versions/ai-light/bin/python tests/llm-tuning-tool/llm-tuning-tool.py --requests-file /tmp/prompts.txt
```

Run a single prompt from the CLI:

```bash
/home/darkangel/.pyenv/versions/ai-light/bin/python tests/llm-tuning-tool/llm-tuning-tool.py --prompt "clear the cue"
```

## Options

- `--ws-url`: websocket endpoint, default `ws://localhost:5001/ws`
- `--prompt`: run one prompt provided directly on the command line
- `--requests-file`: prompt source file
- `--log-dir`: output directory for session logs
- `--assistant-id`: assistant id sent to backend, default `generic`
- `--connect-timeout`: websocket open timeout in seconds
- `--snapshot-timeout`: initial snapshot timeout in seconds
- `--request-timeout`: per-prompt completion timeout in seconds
- `--limit`: only run the first N prompts

All options also support environment variables:

- `LLM_TUNING_WS_URL`
- `LLM_TUNING_REQUESTS_FILE`
- `LLM_TUNING_LOG_DIR`
- `LLM_TUNING_ASSISTANT_ID`
- `LLM_TUNING_CONNECT_TIMEOUT`
- `LLM_TUNING_SNAPSHOT_TIMEOUT`
- `LLM_TUNING_REQUEST_TIMEOUT`
- `LLM_TUNING_LIMIT`

## Log format

Each run writes one JSON file named like:

```text
logs/llm-tuning-session-YYYYMMDDTHHMMSSZ.json
```

The session log contains:

- run metadata: session id, timestamps, ws url, direct prompt, requests file, assistant id
- one result per prompt
- per-prompt transcript entries with direction, timestamp, and raw message
- `final_answer` reconstructed from `llm_delta`
- terminal outcome: `done`, `error`, or `failed`
- summary counts for completed, failed, errored, and proposal-bearing prompts

## Notes

- Confirmed-action prompts can produce more than one proposal in sequence; the tool keeps the same request open and auto-confirms each proposal.
- If the backend never reaches `llm_done` or `llm_error`, the tool records a timeout as `failed` and preserves the partial transcript.

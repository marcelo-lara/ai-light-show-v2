# DMX Node Mock

This service acts as an isolated Art-Net node sidecar for CI and local regression runs.

## What it does

- Listens for Art-Net UDP packets on port `6454`
- Parses `ArtDMX` packets
- Dumps received packet metadata under `tests/dmx-node/artifacts/`
- Exposes a tiny HTTP API for inspection

## Artifacts

- `tests/dmx-node/artifacts/packets.jsonl`: every parsed packet
- `tests/dmx-node/artifacts/latest.json`: most recent packet
- `tests/dmx-node/artifacts/summary.json`: packet counts and latest snapshot

## HTTP API

- `GET /health`
- `GET /latest`
- `GET /frames?limit=50`
- `POST /reset`

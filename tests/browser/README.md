# Browser Regression Tests

This folder contains the browser-driven regression suite for AI Light Show v2.

## Goals

- Exercise the app like a human QA would.
- Find controls by visible or semantic cues such as role, label, and text.
- Avoid test-only DOM tags.
- Record videos and failure artifacts for every run.
- Transcode recorded videos to MP4 for easier sharing and PR artifact review.
- Publish results against the versioned checklist in `checklist.md`.

## Local run

```bash
DMX_NODE_IP=dmx-node docker compose up -d dmx-node frontend backend
docker compose run --rm browser-tests
```

Artifacts are written under `tests/browser/artifacts/`.
Recorded test videos are stored as `.mp4`.

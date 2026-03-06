# QA Browser Automation (Human-Like UI Regression)

This module implements a human-like UI regression runner using **Playwright (Python)**. It drives a real Chromium browser inside Docker to verify frontend behavior using a simple YAML-based Domain Specific Language (DSL).

## 🚀 Quick Start

Run the full QA suite along with the required services:

```bash
docker compose --profile qa up --build --abort-on-container-exit
```

## 📂 Structure

- `runner.py`: The main execution engine. Handles Playwright lifecycle, video recording, and failure artifacts.
- `directives.py`: Implementation of the YAML DSL commands (`goto`, `click`, `expect`).
- `utils.py`: Utility functions for file handling, naming, and artifact rotation.
- `tests/`: Directory containing `.yaml` test definitions.
- `artifacts/`: (Generated at runtime) Stores results for the **last 5 runs**:
  - `last_run.log`: Machine-readable JSON summary of the most recent run (for AI analysis).
  - `20260306_120000_smoke_test.webm`: Timestamped video of the run.
  - `failure_*.png`: Screenshots taken at the moment of failure.
  - `trace_*.zip`: Playwright trace files for deep debugging.

## 📝 Creating & Updating Tests

Tests are authored in YAML. Each test file represents a scenario.

### YAML Schema

```yaml
name: "Descriptive Test Name"
base_url: "http://frontend:5173" # Optional override
steps:
  - goto: "/path"
  - click:
      role: "button" # Preferred (accessibility-first)
      name: "Button Text"
  # OR
  - click:
      css: ".manual-selector"
  - expect:
      visible:
        css: "[data-testid='element-id']"
  - expect:
      count:
        css: ".item-class"
        equals: 5
  - expect:
      text:
        css: "[data-testid='ws-status']"
        matches: "Connected"
        timeout: 15000 # Optional: wait up to 15s for state changes
  - expect:
      texts:
        css: "[data-testid='title']"
        equals: ["Alpha", "Beta", "Gamma"] # Exact ordered match
```

### Best Practices for "Human-Like" Tests

1.  **Use Roles over Selectors**: Prefer `click: { role: "button", name: "Submit" }` over CSS selectors. It mimics how humans find elements and ensures accessibility.
2.  **Stable Selectors**: When CSS is necessary, use `data-testid` attributes. Avoid selectors tied to styling (like `.blue-btn-large`).
3.  **Auto-Waiting**: Playwright automatically waits for elements to be actionable. You don't need manual "sleep" steps.
4.  **Network Idle**: `goto` steps wait for `networkidle` by default to ensure heavy JS/Websocket apps are ready.

## 🛠 Adding New Directives

To add a new capability (e.g., `type`, `hover`, `drag`), update:
1.  `qa/directives.py`: Add a `do_<name>` function and update `run_step`.
2.  `qa/README.md`: Document the new syntax.

## 🔍 Debugging Failures

When a test fails:
1.  Check the **screenshot** in `qa/artifacts/` to see exactly what the browser saw.
2.  Read `last_run.log`: It contains a JSON summary including the error message and call logs.
3.  Open the **Trace ZIP** at [playwright.dev/trace](https://trace.playwright.dev/) to step through the execution, inspect network calls, and view the DOM state at every step.

## ♻️ Artifact Lifecycle

The runner automatically maintains the **last 5 test runs**. Artifacts are prefixed with a `YYYYMMDD_HHMMSS` timestamp. Older runs are deleted to save disk space while preserving enough history to identify intermittent flakiness.

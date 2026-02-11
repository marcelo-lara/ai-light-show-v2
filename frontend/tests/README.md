# E2E tests (Playwright)

These tests assume the stack is already running (frontend on http://localhost:5000, backend+worker+redis via docker compose).

## Run locally
1) Start services in another shell:
   ```bash
   docker compose up --build
   ```
2) From the `frontend` folder install deps and Playwright browsers (first time only):
   ```bash
   npm install
   npx playwright install --with-deps
   ```
3) Run the suite:
   ```bash
   npm run test:e2e
   ```
   Set a custom base URL if needed:
   ```bash
   BASE_URL=http://localhost:5000 npm run test:e2e
   ```

Artifacts (traces, screenshots) are stored in `playwright-report`/`test-results` and kept on failures for debugging.

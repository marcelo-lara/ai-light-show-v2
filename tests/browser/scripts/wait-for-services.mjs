const frontendUrl = process.env.FRONTEND_URL ?? "http://localhost:5173";
const backendUrl = process.env.BACKEND_URL ?? "http://localhost:5001";
const dmxNodeUrl = process.env.DMX_NODE_URL?.trim();
const timeoutMs = Number(process.env.BROWSER_TEST_WAIT_TIMEOUT_MS ?? 120_000);
const pollIntervalMs = Number(process.env.BROWSER_TEST_POLL_INTERVAL_MS ?? 2_000);

async function waitForUrl(url, label) {
  const startedAt = Date.now();

  while (Date.now() - startedAt < timeoutMs) {
    try {
      const response = await fetch(url);
      if (response.ok) {
        console.log(`[wait] ${label} is ready at ${url}`);
        return;
      }
      console.log(`[wait] ${label} responded with ${response.status} at ${url}`);
    } catch (error) {
      console.log(`[wait] ${label} not ready at ${url}: ${error instanceof Error ? error.message : String(error)}`);
    }

    await new Promise((resolve) => setTimeout(resolve, pollIntervalMs));
  }

  throw new Error(`Timed out waiting for ${label} at ${url}`);
}

await waitForUrl(`${backendUrl}/`, "backend");
await waitForUrl(`${frontendUrl}/health`, "frontend");
if (dmxNodeUrl) {
  await waitForUrl(`${dmxNodeUrl}/health`, "dmx-node");
}

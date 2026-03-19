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

async function waitForWebSocket(url, label) {
  const startedAt = Date.now();

  while (Date.now() - startedAt < timeoutMs) {
    try {
      await new Promise((resolve, reject) => {
        const socket = new WebSocket(url);
        const timer = setTimeout(() => {
          socket.close();
          reject(new Error("timeout"));
        }, Math.min(5_000, pollIntervalMs * 2));

        socket.onopen = () => {
          clearTimeout(timer);
          socket.close();
          resolve(undefined);
        };
        socket.onerror = () => {
          clearTimeout(timer);
          reject(new Error("websocket_error"));
        };
        socket.onclose = (event) => {
          if (event.code !== 1000) {
            clearTimeout(timer);
            reject(new Error(`closed_${event.code}`));
          }
        };
      });
      console.log(`[wait] ${label} is ready at ${url}`);
      return;
    } catch (error) {
      console.log(`[wait] ${label} not ready at ${url}: ${error instanceof Error ? error.message : String(error)}`);
    }

    await new Promise((resolve) => setTimeout(resolve, pollIntervalMs));
  }

  throw new Error(`Timed out waiting for ${label} at ${url}`);
}

function toWebSocketUrl(url) {
  const parsed = new URL(url);
  parsed.protocol = parsed.protocol === "https:" ? "wss:" : "ws:";
  parsed.pathname = "/ws";
  parsed.search = "";
  parsed.hash = "";
  return parsed.toString();
}

await waitForUrl(`${backendUrl}/`, "backend");
await waitForUrl(`${frontendUrl}/health`, "frontend");
await waitForWebSocket(toWebSocketUrl(frontendUrl), "frontend websocket");
if (dmxNodeUrl) {
  await waitForUrl(`${dmxNodeUrl}/health`, "dmx-node");
}

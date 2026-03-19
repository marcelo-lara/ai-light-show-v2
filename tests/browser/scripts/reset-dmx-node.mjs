const dmxNodeUrl = process.env.DMX_NODE_URL?.trim();

if (!dmxNodeUrl) {
  console.log("[dmx-node] No DMX_NODE_URL configured; skipping reset.");
  process.exit(0);
}

const response = await fetch(`${dmxNodeUrl}/reset`, { method: "POST" });
if (!response.ok) {
  throw new Error(`Failed to reset DMX node at ${dmxNodeUrl}: ${response.status}`);
}

console.log(`[dmx-node] Reset mock node at ${dmxNodeUrl}`);

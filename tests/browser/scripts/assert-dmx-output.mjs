const dmxNodeUrl = process.env.DMX_NODE_URL?.trim();

if (!dmxNodeUrl) {
  console.log("[dmx-node] No DMX_NODE_URL configured; skipping DMX assertions.");
  process.exit(0);
}

const response = await fetch(`${dmxNodeUrl}/frames?limit=500`);
if (!response.ok) {
  throw new Error(`Failed to fetch DMX frames from ${dmxNodeUrl}: ${response.status}`);
}

const payload = await response.json();
const frames = Array.isArray(payload.frames) ? payload.frames : [];

if (frames.length === 0) {
  throw new Error("DMX node captured no ArtDMX frames during the browser regression run.");
}

const hasFullFrame = frames.some((frame) => frame.length === 512 && frame.opcode === 0x5000);
if (!hasFullFrame) {
  throw new Error("DMX node captured packets, but none matched a full 512-channel ArtDMX frame.");
}

const hasNonZeroFrame = frames.some((frame) => Number(frame.nonzero_count ?? 0) > 0);
if (!hasNonZeroFrame) {
  throw new Error("DMX node captured only zero-valued ArtDMX frames; expected at least one non-zero output frame.");
}

console.log(`[dmx-node] Assertions passed with ${frames.length} captured ArtDMX frames.`);

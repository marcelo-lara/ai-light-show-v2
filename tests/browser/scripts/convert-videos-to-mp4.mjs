import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), "..");
const ARTIFACTS_ROOT = path.join(ROOT, "artifacts", "test-results");

function walk(dir) {
  if (!fs.existsSync(dir)) return [];

  const results = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      results.push(...walk(fullPath));
      continue;
    }
    if (entry.isFile() && entry.name === "video.webm") {
      results.push(fullPath);
    }
  }
  return results;
}

const webmFiles = walk(ARTIFACTS_ROOT);

for (const webmPath of webmFiles) {
  const mp4Path = webmPath.replace(/\.webm$/i, ".mp4");
  const result = spawnSync(
    "ffmpeg",
    [
      "-y",
      "-i",
      webmPath,
      "-c:v",
      "libx264",
      "-pix_fmt",
      "yuv420p",
      "-movflags",
      "+faststart",
      mp4Path,
    ],
    { stdio: "inherit" },
  );

  if (result.status !== 0) {
    console.error(`[video-convert] Failed to convert ${webmPath}`);
    continue;
  }

  fs.unlinkSync(webmPath);
  console.log(`[video-convert] Wrote ${mp4Path}`);
}

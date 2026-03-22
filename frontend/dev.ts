import { contentType } from "@std/media-types/content-type";
import { dirname, extname, fromFileUrl, join, normalize } from "@std/path";
import * as esbuild from "esbuild";
import { renderDocument } from "./src/app/server.ts";

const ROOT = dirname(fromFileUrl(import.meta.url));
const SRC_ROOT = join(ROOT, "src");

let bundleCache = "";
let bundleBuiltAt = 0;

function getWsUrl(req: Request): string {
  const url = new URL(req.url);
  const protocol = url.protocol === "https:" ? "wss" : "ws";
  // The backend is exposed at port 5001 on the host machine.
  // We use the request host (s2.local:5173) and swap the port to 5001.
  const host = url.hostname;
  return `${protocol}://${host}:5001/ws`;
}

async function bundleClient(): Promise<string> {
  const now = Date.now();
  if (bundleCache && now - bundleBuiltAt < 300) return bundleCache;

  const result = await esbuild.build({
    entryPoints: [join(ROOT, "src", "app", "main.ts")],
    bundle: true,
    format: "esm",
    platform: "browser",
    write: false,
    sourcemap: "inline",
    target: ["es2022"],
  });

  const output = result.outputFiles?.[0]?.text ?? "";
  bundleCache = output;
  bundleBuiltAt = now;
  return output;
}

function safePath(pathname: string): string | null {
  const decoded = decodeURIComponent(pathname);
  const normalized = normalize(decoded);
  if (normalized.includes("..")) return null;
  return normalized;
}

async function serveStatic(pathname: string): Promise<Response | null> {
  const resolved = safePath(pathname);
  if (!resolved) {
    return new Response("Bad path", { status: 400 });
  }

  const filePath = join(ROOT, resolved);
  if (!filePath.startsWith(ROOT)) {
    return new Response("Forbidden", { status: 403 });
  }

  try {
    const file = await Deno.readFile(filePath);
    const type = contentType(extname(filePath)) ?? "application/octet-stream";
    return new Response(file, {
      status: 200,
      headers: { "content-type": type },
    });
  } catch {
    return null;
  }
}

Deno.serve({ port: 5173 }, async (req) => {
  const url = new URL(req.url);

  if (url.pathname === "/health") {
    return Response.json({ ok: true });
  }

  if (url.pathname === "/app.js") {
    const js = await bundleClient();
    return new Response(js, {
      status: 200,
      headers: {
        "content-type": "application/javascript; charset=utf-8",
        "cache-control": "no-store",
      },
    });
  }

  if (url.pathname.startsWith("/src/") || url.pathname.endsWith(".css")) {
    const staticResponse = await serveStatic(url.pathname);
    if (staticResponse) return staticResponse;
  }

  const bootstrap = {
    seq: 0,
    state: {},
    wsUrl: getWsUrl(req),
  };

  const html = renderDocument({ bootstrap });
  return new Response(html, {
    status: 200,
    headers: {
      "content-type": "text/html; charset=utf-8",
      "cache-control": "no-store",
    },
  });
});

esbuild.initialize({});

globalThis.addEventListener("unload", () => {
  esbuild.stop();
});

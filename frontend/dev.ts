import { contentType } from "@std/media-types/content-type";
import { dirname, extname, fromFileUrl, join, normalize } from "@std/path";
import * as esbuild from "esbuild";
import { renderDocument } from "./src/app/server.ts";

const ROOT = dirname(fromFileUrl(import.meta.url));
const SRC_ROOT = join(ROOT, "src");

let bundleCache = "";
let bundleBuiltAt = 0;

function getBackendHost(req: Request): string {
  const url = new URL(req.url);
  const configuredHost = Deno.env.get("BACKEND_WS_HOST")?.trim();
  const useConfiguredHost = Boolean(configuredHost) && url.hostname === "frontend";
  return useConfiguredHost ? configuredHost! : `${url.hostname}:5001`;
}

function getBackendHttpOrigin(req: Request): string {
  const url = new URL(req.url);
  const protocol = url.protocol === "https:" ? "https" : "http";
  return `${protocol}://${getBackendHost(req)}`;
}

function getBackendWsUrl(req: Request): string {
  const url = new URL(req.url);
  const protocol = url.protocol === "https:" ? "wss" : "ws";
  return `${protocol}://${getBackendHost(req)}/ws`;
}

function getFrontendWsUrl(req: Request): string {
  const url = new URL(req.url);
  const protocol = url.protocol === "https:" ? "wss" : "ws";
  return `${protocol}://${url.host}/ws`;
}

function proxyWsMessage(target: WebSocket, data: string | ArrayBufferLike | Blob | ArrayBufferView) {
  if (typeof data === "string" || data instanceof Blob || data instanceof ArrayBuffer) {
    target.send(data);
    return;
  }
  target.send(data.buffer.slice(data.byteOffset, data.byteOffset + data.byteLength));
}

function proxyWebSocket(req: Request): Response {
  const { socket: clientSocket, response } = Deno.upgradeWebSocket(req);
  const upstream = new WebSocket(getBackendWsUrl(req));
  const pendingMessages: Array<string | ArrayBufferLike | Blob | ArrayBufferView> = [];

  const closeBoth = (code = 1011, reason = "proxy_closed") => {
    if (clientSocket.readyState === WebSocket.OPEN) clientSocket.close(code, reason);
    if (upstream.readyState === WebSocket.OPEN || upstream.readyState === WebSocket.CONNECTING) upstream.close(code, reason);
  };

  clientSocket.onmessage = (event) => {
    if (upstream.readyState === WebSocket.OPEN) {
      proxyWsMessage(upstream, event.data);
      return;
    }
    pendingMessages.push(event.data);
  };
  clientSocket.onclose = () => closeBoth(1000, "client_closed");
  clientSocket.onerror = () => closeBoth(1011, "client_error");

  upstream.onopen = () => {
    while (pendingMessages.length > 0) {
      const message = pendingMessages.shift();
      if (message !== undefined) proxyWsMessage(upstream, message);
    }
  };
  upstream.onmessage = (event) => {
    if (clientSocket.readyState === WebSocket.OPEN) {
      proxyWsMessage(clientSocket, event.data);
    }
  };
  upstream.onclose = (event) => {
    if (clientSocket.readyState === WebSocket.OPEN || clientSocket.readyState === WebSocket.CONNECTING) {
      clientSocket.close(event.code || 1000, event.reason || "upstream_closed");
    }
  };
  upstream.onerror = () => closeBoth(1011, "upstream_error");

  return response;
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

  if (url.pathname === "/ws") {
    return proxyWebSocket(req);
  }

  if (url.pathname === "/health") {
    return Response.json({ ok: true });
  }

  if (url.pathname === "/app.js") {
    const js = await bundleClient();
    return new Response(js, {
      status: 200,
      headers: { "content-type": "application/javascript; charset=utf-8" },
    });
  }

  if (url.pathname.startsWith("/src/") || url.pathname.endsWith(".css")) {
    const staticResponse = await serveStatic(url.pathname);
    if (staticResponse) return staticResponse;
  }

  const bootstrap = {
    seq: 0,
    state: {},
    wsUrl: getFrontendWsUrl(req),
    backendHttpOrigin: getBackendHttpOrigin(req),
  };

  const html = renderDocument({ bootstrap });
  return new Response(html, {
    status: 200,
    headers: { "content-type": "text/html; charset=utf-8" },
  });
});

esbuild.initialize({});

globalThis.addEventListener("unload", () => {
  esbuild.stop();
});

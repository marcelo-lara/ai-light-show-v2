import json
import os
import socket
import threading
import time
from collections import deque
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

ARTNET_PORT = int(os.getenv("DMX_NODE_PORT", "6454"))
HTTP_PORT = int(os.getenv("DMX_NODE_HTTP_PORT", "9010"))
MAX_IN_MEMORY_FRAMES = int(os.getenv("DMX_NODE_MAX_FRAMES", "500"))
DUMP_DIR = Path(os.getenv("DMX_NODE_DUMP_DIR", "/app/tests/dmx-node/artifacts"))

frames = deque(maxlen=MAX_IN_MEMORY_FRAMES)
frames_lock = threading.Lock()
packet_count = 0
started_at = time.time()


def ensure_dump_dir() -> None:
    DUMP_DIR.mkdir(parents=True, exist_ok=True)


def json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, default=json_default) + "\n", encoding="utf-8")


def append_jsonl(path: Path, payload: Any) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, default=json_default) + "\n")


def parse_artnet_packet(data: bytes, source_ip: str) -> dict[str, Any] | None:
    if len(data) < 18 or not data.startswith(b"Art-Net\x00"):
        return None

    opcode = int.from_bytes(data[8:10], "little")
    if opcode != 0x5000:
        return None
    protocol_version = int.from_bytes(data[10:12], "big")
    sequence = data[12]
    physical = data[13]
    universe = int.from_bytes(data[14:16], "little")
    length = int.from_bytes(data[16:18], "big")
    dmx_data = data[18:18 + length]

    nonzero_channels = [
        {"channel": index + 1, "value": value}
        for index, value in enumerate(dmx_data)
        if value
    ]

    return {
        "timestamp": time.time(),
        "source_ip": source_ip,
        "opcode": opcode,
        "protocol_version": protocol_version,
        "sequence": sequence,
        "physical": physical,
        "universe": universe,
        "length": length,
        "nonzero_count": len(nonzero_channels),
        "max_value": max(dmx_data, default=0),
        "nonzero_channels": nonzero_channels,
        "data_hex": dmx_data.hex(),
    }


def persist_frame(frame: dict[str, Any]) -> None:
    ensure_dump_dir()
    append_jsonl(DUMP_DIR / "packets.jsonl", frame)
    write_json(DUMP_DIR / "latest.json", frame)


def persist_summary() -> None:
    ensure_dump_dir()
    with frames_lock:
        latest = frames[-1] if frames else None
        summary = {
            "started_at": started_at,
            "packet_count": packet_count,
            "stored_frames": len(frames),
            "latest": latest,
        }
    write_json(DUMP_DIR / "summary.json", summary)


def reset_state() -> None:
    global packet_count
    with frames_lock:
        frames.clear()
        packet_count = 0
    ensure_dump_dir()
    for path in ("packets.jsonl", "latest.json", "summary.json"):
        target = DUMP_DIR / path
        if target.exists():
            target.unlink()
    persist_summary()


def udp_listener() -> None:
    global packet_count
    ensure_dump_dir()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", ARTNET_PORT))
    print(f"[dmx-node] Listening for Art-Net UDP on 0.0.0.0:{ARTNET_PORT}", flush=True)

    while True:
        data, addr = sock.recvfrom(4096)
        frame = parse_artnet_packet(data, addr[0])
        if frame is None:
            continue

        with frames_lock:
            frames.append(frame)
            packet_count += 1

        persist_frame(frame)
        persist_summary()


class RequestHandler(BaseHTTPRequestHandler):
    def _send_json(self, payload: Any, status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload, indent=2, default=json_default).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)

        if parsed.path == "/health":
            self._send_json({
                "ok": True,
                "udp_port": ARTNET_PORT,
                "http_port": HTTP_PORT,
                "dump_dir": str(DUMP_DIR),
            })
            return

        if parsed.path == "/frames":
            query = parse_qs(parsed.query)
            limit = int(query.get("limit", ["50"])[0])
            with frames_lock:
                items = list(frames)[-max(0, limit):]
            self._send_json({
                "packet_count": packet_count,
                "frames": items,
            })
            return

        if parsed.path == "/latest":
            with frames_lock:
                latest = frames[-1] if frames else None
            self._send_json({
                "packet_count": packet_count,
                "latest": latest,
            })
            return

        self._send_json({"error": "not_found"}, status=HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/reset":
            reset_state()
            self._send_json({"ok": True, "packet_count": 0})
            return

        self._send_json({"error": "not_found"}, status=HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args: Any) -> None:
        print(f"[dmx-node] {self.address_string()} - {format % args}", flush=True)


if __name__ == "__main__":
    reset_state()
    threading.Thread(target=udp_listener, daemon=True).start()
    print(f"[dmx-node] HTTP API listening on 0.0.0.0:{HTTP_PORT}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", HTTP_PORT), RequestHandler).serve_forever()

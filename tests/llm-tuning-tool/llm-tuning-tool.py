from __future__ import annotations

import argparse
import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from websockets.exceptions import ConnectionClosed
from websockets.sync.client import connect


def iso_now() -> str:
	return datetime.now(timezone.utc).isoformat()


def build_parser() -> argparse.ArgumentParser:
	parser = argparse.ArgumentParser(description="Run one LLM prompt per websocket session and log the responses.")
	parser.add_argument("--ws-url", default=os.getenv("LLM_TUNING_WS_URL", "ws://localhost:5001/ws"))
	parser.add_argument("--requests-file", type=Path, default=Path(os.getenv("LLM_TUNING_REQUESTS_FILE", str(Path(__file__).resolve().parent / "user-requests.txt"))))
	parser.add_argument("--log-dir", type=Path, default=Path(os.getenv("LLM_TUNING_LOG_DIR", str(Path(__file__).resolve().parent / "logs"))))
	parser.add_argument("--assistant-id", default=os.getenv("LLM_TUNING_ASSISTANT_ID", "generic"))
	parser.add_argument("--connect-timeout", type=float, default=float(os.getenv("LLM_TUNING_CONNECT_TIMEOUT", "10")))
	parser.add_argument("--snapshot-timeout", type=float, default=float(os.getenv("LLM_TUNING_SNAPSHOT_TIMEOUT", "10")))
	parser.add_argument("--request-timeout", type=float, default=float(os.getenv("LLM_TUNING_REQUEST_TIMEOUT", "120")))
	parser.add_argument("--limit", type=int, default=int(os.getenv("LLM_TUNING_LIMIT", "0")))
	return parser


def load_prompts(path: Path, limit: int) -> list[str]:
	prompts = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
	return prompts[:limit] if limit > 0 else prompts


def session_log_path(log_dir: Path) -> Path:
	stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
	return log_dir / f"llm-tuning-session-{stamp}.json"


def write_session_log(path: Path, payload: dict) -> None:
	path.parent.mkdir(parents=True, exist_ok=True)
	path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def compact_message(message: dict) -> dict:
	if message.get("type") != "snapshot":
		return message
	return {"type": "snapshot", "seq": message.get("seq")}


def recv_json(ws, timeout: float) -> dict:
	raw = ws.recv(timeout=timeout)
	if not isinstance(raw, str):
		raise ValueError(f"expected text websocket frame, got {type(raw).__name__}")
	return json.loads(raw)


def wait_for_snapshot(ws, timeout: float) -> list[dict]:
	deadline = time.monotonic() + timeout
	transcript: list[dict] = []
	while True:
		remaining = deadline - time.monotonic()
		if remaining <= 0:
			raise TimeoutError("timed out waiting for initial snapshot")
		message = recv_json(ws, remaining)
		transcript.append({"direction": "in", "message": compact_message(message), "received_at": iso_now()})
		if message.get("type") == "snapshot":
			return transcript


def send_intent(ws, name: str, payload: dict, request_id: str, transcript: list[dict]) -> None:
	message = {"type": "intent", "req_id": request_id, "name": name, "payload": payload}
	ws.send(json.dumps(message))
	transcript.append({"direction": "out", "message": message, "sent_at": iso_now()})


def run_prompt(index: int, prompt: str, args: argparse.Namespace) -> dict:
	started_at = iso_now()
	request_id = f"prompt-{index}-{uuid.uuid4().hex[:8]}"
	transcript: list[dict] = []
	deltas: list[str] = []
	proposal_count = 0
	try:
		with connect(args.ws_url, open_timeout=args.connect_timeout, close_timeout=5, max_size=2_000_000) as ws:
			transcript.extend(wait_for_snapshot(ws, args.snapshot_timeout))
			send_intent(ws, "llm.send_prompt", {"prompt": prompt, "assistant_id": args.assistant_id}, request_id, transcript)
			deadline = time.monotonic() + args.request_timeout
			while True:
				remaining = deadline - time.monotonic()
				if remaining <= 0:
					raise TimeoutError("timed out waiting for llm_done or llm_error")
				message = recv_json(ws, remaining)
				data: dict = message["data"] if isinstance(message.get("data"), dict) else {}
				if message.get("type") != "event" or data.get("request_id") != request_id:
					continue
				transcript.append({"direction": "in", "message": message, "received_at": iso_now()})
				kind = message.get("message")
				if kind == "llm_delta":
					deltas.append(str(data.get("delta", "")))
				elif kind == "llm_action_proposed":
					proposal_count += 1
					confirm_id = f"confirm-{index}-{uuid.uuid4().hex[:8]}"
					send_intent(ws, "llm.confirm_action", {"request_id": request_id, "action_id": data.get("action_id")}, confirm_id, transcript)
				elif kind == "llm_done":
					return {
						"index": index,
						"prompt": prompt,
						"request_id": request_id,
						"started_at": started_at,
						"ended_at": iso_now(),
						"status": "done",
						"proposal_count": proposal_count,
						"final_answer": "".join(deltas),
						"transcript": transcript,
						"terminal_event": message,
					}
				elif kind == "llm_error":
					return {
						"index": index,
						"prompt": prompt,
						"request_id": request_id,
						"started_at": started_at,
						"ended_at": iso_now(),
						"status": "error",
						"proposal_count": proposal_count,
						"final_answer": "".join(deltas),
						"transcript": transcript,
						"terminal_event": message,
					}
	except (ConnectionClosed, OSError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
		return {
			"index": index,
			"prompt": prompt,
			"request_id": request_id,
			"started_at": started_at,
			"ended_at": iso_now(),
			"status": "failed",
			"proposal_count": proposal_count,
			"final_answer": "".join(deltas),
			"transcript": transcript,
			"error": f"{type(exc).__name__}: {exc}",
		}


def summarize(results: list[dict]) -> dict:
	return {
		"total": len(results),
		"completed": sum(1 for item in results if item["status"] == "done"),
		"failed": sum(1 for item in results if item["status"] == "failed"),
		"errored": sum(1 for item in results if item["status"] == "error"),
		"with_proposals": sum(1 for item in results if item.get("proposal_count", 0) > 0),
	}


def main() -> int:
	args = build_parser().parse_args()
	prompts = load_prompts(args.requests_file, args.limit)
	session = {
		"session_id": uuid.uuid4().hex,
		"started_at": iso_now(),
		"ws_url": args.ws_url,
		"requests_file": str(args.requests_file),
		"assistant_id": args.assistant_id,
		"results": [],
	}
	log_path = session_log_path(args.log_dir)
	write_session_log(log_path, session)
	total = len(prompts)
	for index, prompt in enumerate(prompts, start=1):
		result = run_prompt(index, prompt, args)
		session["results"].append(result)
		session["summary"] = summarize(session["results"])
		session["updated_at"] = iso_now()
		write_session_log(log_path, session)
		status = result["status"]
		print(f"[{index}/{total}] {status}: {prompt}")
	session["ended_at"] = iso_now()
	session["summary"] = summarize(session["results"])
	write_session_log(log_path, session)
	print(f"session log: {log_path}")
	return 0 if session["summary"]["failed"] == 0 and session["summary"]["errored"] == 0 else 1


if __name__ == "__main__":
	raise SystemExit(main())

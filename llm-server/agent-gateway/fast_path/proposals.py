from typing import Any, Dict, List

import orjson


def _describe_cue_add_entries(entries: List[Dict[str, Any]]) -> str:
    fixtures = ", ".join(dict.fromkeys(str(entry.get("fixture_id") or "") for entry in entries if str(entry.get("fixture_id") or "")))
    unique_times = list(dict.fromkeys(float(entry.get("time", 0.0) or 0.0) for entry in entries))
    time_text = f"{(unique_times[0] if unique_times else 0.0):.3f}s" if len(unique_times) <= 1 else ", ".join(f"{time_value:.3f}s" for time_value in unique_times)
    if entries:
        first_effect = str(entries[0].get("effect") or "effect")
        first_data = entries[0].get("data") or {}
        if first_effect == "blackout":
            return f"Turn off {fixtures} at {time_text}."
        if first_effect == "fade_out":
            return f"Add fade_out to {fixtures} at {time_text}."
        if first_effect == "flash":
            channels = first_data.get("channels")
            if isinstance(channels, list) and len(channels) == 1 and str(channels[0] or "").strip():
                return f"Add {str(channels[0]).strip().lower()} flash to {fixtures} at {time_text}."
        if first_effect == "move_to_poi":
            target_poi = str(first_data.get("target_POI") or first_data.get("poi") or first_data.get("POI") or "").strip()
            if target_poi:
                return f"Move {fixtures} to {target_poi} at {time_text}."
        if first_effect == "seek":
            if str(first_data.get("start_POI") or "").strip() and str(first_data.get("subject_POI") or "").strip():
                return f"Add seek on {fixtures} from {first_data['start_POI']} to {first_data['subject_POI']} at {time_text}."
        if first_effect == "sweep":
            start_poi = str(first_data.get("start_POI") or "").strip()
            subject_poi = str(first_data.get("subject_POI") or "").strip()
            end_poi = str(first_data.get("end_POI") or "").strip()
            if start_poi and subject_poi and end_poi:
                return f"Add sweep on {fixtures} from {start_poi} through {subject_poi} to {end_poi} at {time_text}."
            if start_poi and subject_poi:
                return f"Add sweep on {fixtures} from {start_poi} through {subject_poi} at {time_text}."
        if first_effect == "full":
            if not first_data:
                return f"Set {fixtures} to full at {time_text}."
            for color_name, rgb in {"blue": {"red": 0, "green": 0, "blue": 255}, "red": {"red": 255, "green": 0, "blue": 0}, "green": {"red": 0, "green": 255, "blue": 0}, "white": {"red": 255, "green": 255, "blue": 255}, "yellow": {"red": 255, "green": 255, "blue": 0}, "cyan": {"red": 0, "green": 255, "blue": 255}, "magenta": {"red": 255, "green": 0, "blue": 255}, "purple": {"red": 128, "green": 0, "blue": 255}, "orange": {"red": 255, "green": 128, "blue": 0}, "pink": {"red": 255, "green": 105, "blue": 180}}.items():
                if all(int(first_data.get(channel, -1)) == value for channel, value in rgb.items()):
                    return f"Set {fixtures} to {color_name} at {time_text}."
    return f"Add {str(entries[0].get('effect') or 'effect') if entries else 'effect'} to {fixtures} at {time_text}."


def _proposal_for_tool(tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    action_id = f"proposal-{abs(hash(orjson.dumps(args).decode('utf-8'))) % 1000000}"
    if tool_name == "propose_cue_add_entries":
        entries = list(args.get("entries") or [])
        return {"type": "proposal", "action_id": action_id, "tool_name": tool_name, "arguments": {"entries": entries}, "title": "Confirm cue add", "summary": _describe_cue_add_entries(entries)}
    if tool_name == "propose_cue_clear_all":
        return {"type": "proposal", "action_id": action_id, "tool_name": tool_name, "arguments": {}, "title": "Confirm cue sheet clear", "summary": "Remove all cue items from the cue sheet."}
    if tool_name == "propose_cue_clear_range":
        start_time = float(args.get("start_time", 0.0))
        end_time = float(args.get("end_time", 0.0))
        return {"type": "proposal", "action_id": action_id, "tool_name": tool_name, "arguments": args, "title": "Confirm cue clear", "summary": f"Remove cue items from {start_time:.3f}s to {end_time:.3f}s."}
    return {"type": "proposal", "action_id": action_id, "tool_name": tool_name, "arguments": args, "title": "Confirm chaser apply", "summary": f"Apply chaser {args.get('chaser_id')} at {float(args.get('start_time', 0.0)):.3f}s for {int(args.get('repetitions', 1))} repetitions."}
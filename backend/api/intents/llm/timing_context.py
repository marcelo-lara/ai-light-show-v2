from __future__ import annotations

from typing import Any, Dict, List

from api.intents.llm.song_context import build_song_sections_payload


def build_section_by_name_payload(manager, section_name: str) -> Dict[str, Any] | None:
	lookup = str(section_name or "").strip().lower()
	if not lookup:
		return None
	for section in _sections(manager):
		if str(section.get("name") or "").strip().lower() == lookup:
			return {
				**section,
				"answer": f"The {section['name']} section runs from {section['start_s']:g} to {section['end_s']:g} seconds.",
			}
	return None


def build_section_at_time_payload(manager, time_s: float) -> Dict[str, Any] | None:
	point = float(time_s)
	sections = _sections(manager)
	for index, section in enumerate(sections):
		start_s = float(section.get("start_s") or 0.0)
		end_s = float(section.get("end_s") or 0.0)
		is_last = index == len(sections) - 1
		if start_s <= point < end_s or (is_last and start_s <= point <= end_s):
			return {
				**section,
				"answer": f"{point:g} seconds is in the {section['name']} section.",
			}
	return None


def _sections(manager) -> List[Dict[str, Any]]:
	return list(build_song_sections_payload(manager).get("sections", []))

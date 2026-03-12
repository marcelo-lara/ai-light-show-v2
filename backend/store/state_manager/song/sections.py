# pyright: reportAttributeAccessIssue=false

from typing import Any, Dict, List

from store.services.section_persistence import normalize_sections_input

class StateSongSectionsMixin:
    async def save_song_sections(self, sections: List[Dict[str, Any]]) -> Dict[str, Any]:
        async with self.lock:
            if not self.current_song:
                return {"ok": False, "reason": "no_song_loaded"}

            ok, normalized = normalize_sections_input(sections)
            if not ok:
                return normalized

            # Migrate legacy structures returned by `normalize_sections_input` 
            # to the new format to persist with `.update_sections()`
            parts = normalized.get("parts", {})
            new_sections = []
            for name, rng in parts.items():
                if isinstance(rng, list) and len(rng) >= 2:
                    new_sections.append({
                        "name": str(name),
                        "start_s": float(rng[0]),
                        "end_s": float(rng[1])
                    })

            self.current_song.update_sections(new_sections)
            self.song_length_seconds = self._infer_song_length_seconds(self.current_song)
            
            return {"ok": True, "parts": parts}

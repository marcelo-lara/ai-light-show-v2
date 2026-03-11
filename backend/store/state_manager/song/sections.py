# pyright: reportAttributeAccessIssue=false

from typing import Any, Dict, List

from store.services.section_persistence import normalize_sections_input, persist_parts_to_meta


class StateSongSectionsMixin:
    async def save_song_sections(self, sections: List[Dict[str, Any]]) -> Dict[str, Any]:
        async with self.lock:
            if not self.current_song:
                return {"ok": False, "reason": "no_song_loaded"}

            ok, normalized = normalize_sections_input(sections)
            if not ok:
                return normalized

            parts = normalized["parts"]
            self.current_song.metadata.parts = parts
            self.song_length_seconds = self._infer_song_length_seconds(self.current_song.metadata)

            song_filename = self.current_song.filename
            persist_parts_to_meta(
                song_filename=song_filename,
                parts=parts,
                meta_candidates=self._meta_candidates(song_filename),
                meta_path=self.meta_path,
            )
            return {"ok": True, "parts": parts}

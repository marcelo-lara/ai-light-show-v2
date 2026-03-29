from __future__ import annotations

import argparse
import os
from pathlib import Path

from src.song_meta import load_sections, song_meta_dir, song_name

META_PATH = os.environ.get("META_PATH", "/app/meta")


def _render_markdown(song: str, sections: list[dict[str, object]]) -> str:
    lines = [f"# {song} - Light Show", ""]
    for section in sections:
        lines.append(f"## {section['name']} [{section['start_s']}-{section['end_s']}]")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def generate_md_file(song_path: str | Path, meta_path: str | Path = META_PATH) -> Path | None:
    meta_dir = song_meta_dir(song_path, meta_path)
    sections = load_sections(meta_dir)
    if not sections:
        return None
    output_path = meta_dir / f"{song_name(song_path)}.md"
    output_path.write_text(_render_markdown(song_name(song_path), sections), encoding="utf-8")
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate song markdown from analyzer sections")
    parser.add_argument("song_path", type=str, help="Path to the source song file")
    parser.add_argument("--meta-path", type=str, default=META_PATH, help="Path to the analyzer meta root")
    args = parser.parse_args()

    output_path = generate_md_file(args.song_path, meta_path=args.meta_path)
    if output_path is None:
        print(f"No sections metadata found for {Path(args.song_path).stem}")
        return 1
    print(f"Generated markdown file: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
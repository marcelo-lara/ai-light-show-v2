from pathlib import Path

from store.dmx_canvas import DMX_CHANNELS, DMXCanvas


def dump_named_canvas_debug(
    *,
    backend_path: Path,
    file_stem: str,
    canvas: DMXCanvas | None,
    max_used_channel: int,
) -> Path | None:
    if not canvas:
        return None

    cues_path = backend_path / "cues"
    cues_path.mkdir(parents=True, exist_ok=True)
    debug_file = cues_path / f"{file_stem}.canvas.debug.log"
    frames_written = 0
    max_channel = max_used_channel or DMX_CHANNELS
    max_channel = max(1, min(DMX_CHANNELS, int(max_channel)))

    with open(debug_file, "w") as handle:
        for frame_index in range(canvas.total_frames):
            view = canvas.frame_view(frame_index)
            if not any(byte != 0 for byte in view[:max_channel]):
                continue
            time_sec = frame_index / float(canvas.fps)
            hex_pairs = ".".join(f"{int(byte):02X}" for byte in view[:max_channel])
            handle.write(f"[{time_sec:.3f}] {hex_pairs}\n")
            frames_written += 1

    print(f"[DMX CANVAS] dumped debug file '{debug_file}' — frames={frames_written}", flush=True)
    return debug_file


def dump_canvas_debug(
    *,
    backend_path: Path,
    song_filename: str,
    canvas: DMXCanvas | None,
    max_used_channel: int,
) -> None:
    dump_named_canvas_debug(
        backend_path=backend_path,
        file_stem=song_filename,
        canvas=canvas,
        max_used_channel=max_used_channel,
    )

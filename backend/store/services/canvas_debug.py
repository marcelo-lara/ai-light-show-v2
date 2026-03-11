from pathlib import Path

from store.dmx_canvas import DMX_CHANNELS, DMXCanvas


def dump_canvas_debug(
    *,
    backend_path: Path,
    song_filename: str,
    canvas: DMXCanvas | None,
    max_used_channel: int,
) -> None:
    if not canvas:
        return

    cues_path = backend_path / "cues"
    cues_path.mkdir(parents=True, exist_ok=True)
    debug_file = cues_path / f"{song_filename}.canvas.debug.log"
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

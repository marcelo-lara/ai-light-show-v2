from datetime import date
from pathlib import Path
from struct import pack

from store.dmx_canvas import DMX_CHANNELS, DMXCanvas


def build_show_name(show_date: date | None = None) -> str:
    current_date = show_date or date.today()
    return f"show_{current_date.strftime('%Y%m%d')}"


def build_named_canvas_binary_path(*, backend_path: Path, song_filename: str, show_date: date | None = None) -> Path:
    return backend_path.parent / "data" / "shows" / f"{song_filename}.{build_show_name(show_date)}.dmx"


def dump_named_canvas_binary(
    *,
    backend_path: Path,
    song_filename: str,
    canvas: DMXCanvas | None,
    show_date: date | None = None,
) -> Path | None:
    if not canvas:
        return None

    binary_file = build_named_canvas_binary_path(
        backend_path=backend_path,
        song_filename=song_filename,
        show_date=show_date,
    )
    binary_file.parent.mkdir(parents=True, exist_ok=True)

    with open(binary_file, "wb") as handle:
        handle.write(
            pack(
                "<4sHHII16s",
                b"DMXP",
                1,
                1,
                int(canvas.total_frames),
                int(canvas.fps),
                b"\x00" * 16,
            )
        )
        for frame_index in range(canvas.total_frames):
            timestamp_ms = int(round((frame_index * 1000.0) / float(canvas.fps)))
            handle.write(pack("<I", timestamp_ms))
            handle.write(canvas.frame_view(frame_index))

    print(f"[DMX CANVAS] dumped binary show '{binary_file}' — frames={canvas.total_frames}", flush=True)
    return binary_file


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
    debug_file = cues_path / f"{file_stem}.dmx.log"
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

    print(f"[DMX CANVAS] dumped DMX log '{debug_file}' — frames={frames_written}", flush=True)
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


def dump_canvas_binary(
    *,
    backend_path: Path,
    song_filename: str,
    canvas: DMXCanvas | None,
    show_date: date | None = None,
) -> Path | None:
    return dump_named_canvas_binary(
        backend_path=backend_path,
        song_filename=song_filename,
        canvas=canvas,
        show_date=show_date,
    )

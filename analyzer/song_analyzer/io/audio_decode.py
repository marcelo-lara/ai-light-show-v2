"""Audio decoding utilities."""

import subprocess
import soundfile as sf
from pathlib import Path


def decode_mp3_to_wav(mp3_path: Path, wav_path: Path) -> dict:
    """Decode MP3 to WAV using ffmpeg and return metadata."""

    # Ensure output directory exists
    wav_path.parent.mkdir(parents=True, exist_ok=True)

    # Use ffmpeg to decode
    cmd = [
        'ffmpeg', '-i', str(mp3_path),
        '-acodec', 'pcm_s16le',  # 16-bit PCM
        '-ar', '44100',  # 44.1kHz sample rate
        '-ac', '2',  # Stereo
        '-y',  # Overwrite
        str(wav_path)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr}")

    # Get metadata from the decoded file
    info = sf.info(wav_path)

    return {
        'duration_s': info.duration,
        'sample_rate_hz': info.samplerate,
        'channels': info.channels
    }
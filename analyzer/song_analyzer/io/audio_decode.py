import subprocess
from pathlib import Path
import soundfile as sf


def decode_to_wav(input_file: Path, out_wav: Path):
    # Use ffmpeg for robust decoding
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_file),
        "-ar",
        "44100",
        "-ac",
        "2",
        str(out_wav),
    ]
    subprocess.check_call(cmd)
    # read metadata
    with sf.SoundFile(str(out_wav)) as sf_f:
        frames = len(sf_f)
        sr = sf_f.samplerate
        channels = sf_f.channels
        duration = frames / float(sr)
    return {"decoded_wav": str(out_wav), "duration_s": duration, "sample_rate_hz": sr, "channels": channels}

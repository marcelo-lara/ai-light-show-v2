"""Demucs model wrapper for stem separation."""

import torch
from demucs import pretrained
from demucs.apply import apply_model
from pathlib import Path


class DemucsSeparator:
    """Wrapper for Demucs stem separation."""

    def __init__(self, model_name: str = "htdemucs_ft", device: str = "auto"):
        self.model_name = model_name
        self.device = self._resolve_device(device)

        # Load model
        self.model = pretrained.get_model(model_name)
        self.model.to(self.device)
        self.model.eval()

    def _resolve_device(self, device: str) -> str:
        """Resolve device string to actual device."""
        if device == "auto":
            return "cuda" if torch.cuda.is_available() else "cpu"
        return device

    def separate(self, audio_path: Path, output_dir: Path) -> dict:
        """Separate stems from audio file."""

        # Load audio
        wav, sr = self._load_audio(audio_path)

        # Apply model (expects [batch, channels, samples])
        wav = wav.unsqueeze(0)  # Add batch dimension
        with torch.no_grad():
            stems = apply_model(self.model, wav, device=self.device)

        # Remove batch dimension
        stems = stems.squeeze(0)  # [4, channels, samples]

        # Save stems
        stem_names = ["drums", "bass", "vocals", "other"]
        stem_paths = {}

        for i, stem_name in enumerate(stem_names):
            stem_wav = stems[i]  # [channels, samples]
            stem_path = output_dir / f"{stem_name}.wav"
            self._save_audio(stem_wav, sr, stem_path)
            stem_paths[stem_name] = str(stem_path)

        return {
            "model": {
                "name": "demucs",
                "variant": self.model_name,
                "device": self.device
            },
            "stems": stem_paths
        }

    def _load_audio(self, path: Path):
        """Load audio file."""
        import soundfile as sf
        import torch
        import numpy as np

        wav, sr = sf.read(str(path))

        # Ensure stereo
        if wav.ndim == 1:
            wav = np.stack([wav, wav], axis=1)  # mono to stereo
        elif wav.shape[1] == 1:
            wav = np.repeat(wav, 2, axis=1)  # mono to stereo

        # Convert to tensor: [channels, samples]
        wav = torch.from_numpy(wav.T).float()
        return wav, sr

    def _save_audio(self, wav, sr, path: Path):
        """Save audio to file."""
        import soundfile as sf
        # wav is [channels, samples], convert to [samples, channels] for soundfile
        wav = wav.T.cpu().numpy()
        sf.write(str(path), wav, sr)
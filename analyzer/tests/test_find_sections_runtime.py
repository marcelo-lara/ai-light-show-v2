from __future__ import annotations

import sys
import types
from pathlib import Path

from src.musical_structure.hf_models import _REMOTE_CACHE, predict_sections
from src.musical_structure.registry import ModelCandidate


def test_predict_sections_preserves_remote_model_cuda_access(monkeypatch, tmp_path: Path) -> None:
    import torch

    observations: list[tuple[object, ...]] = []

    class FakeRemoteModel:
        def eval(self) -> "FakeRemoteModel":
            observations.append(("eval",))
            return self

        def __call__(self, *, audio_file: str, return_segments: bool) -> object:
            observations.append(("call", return_segments, torch.cuda.is_available(), torch.cuda.device_count(), audio_file))
            if return_segments:
                return types.SimpleNamespace(segments=[{"label": "Verse", "start": 0.0, "end": 4.0}])
            return types.SimpleNamespace(class_logits=None)

    class FakeAutoModel:
        @staticmethod
        def from_pretrained(model_id: str, trust_remote_code: bool = False) -> FakeRemoteModel:
            observations.append(("load", model_id, trust_remote_code, torch.cuda.is_available(), torch.cuda.device_count()))
            return FakeRemoteModel()

    fake_transformers = types.SimpleNamespace(AutoModel=FakeAutoModel)
    monkeypatch.setitem(sys.modules, "transformers", fake_transformers)
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    monkeypatch.setattr(torch.cuda, "device_count", lambda: 1)
    _REMOTE_CACHE.clear()

    audio_path = tmp_path / "song.wav"
    audio_path.write_bytes(b"stub")
    candidate = ModelCandidate(
        name="music-section-detection",
        model_id="fake/section-model",
        loader="remote-segmentation",
        window_s=0.0,
        stride_s=0.0,
        trust_remote_code=True,
    )

    result = predict_sections(candidate, audio_path)

    assert result["items"][0]["label"] == "Verse"
    assert ("load", "fake/section-model", True, True, 1) in observations
    assert ("call", True, True, 1, str(audio_path)) in observations
    assert ("call", False, True, 1, str(audio_path)) in observations
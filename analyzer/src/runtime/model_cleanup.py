from __future__ import annotations

import gc
import logging

LOGGER = logging.getLogger(__name__)


def release_model_memory() -> None:
    for release in (_release_musical_structure_models, _release_song_feature_models):
        try:
            release()
        except Exception as exc:
            LOGGER.warning("Model cleanup hook failed: %s", exc)
    gc.collect()
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            if hasattr(torch.cuda, "ipc_collect"):
                torch.cuda.ipc_collect()
    except Exception:
        return


def _release_musical_structure_models() -> None:
    from ..musical_structure.hf_models import release_model_caches

    release_model_caches()


def _release_song_feature_models() -> None:
    from ..song_features.extractor import release_model_cache

    release_model_cache()
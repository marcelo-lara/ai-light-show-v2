import pytest

from services.cue_helpers import beatToTimeMs


def test_beat_to_time_ms_conversion():
    assert beatToTimeMs(1.0, 120.0) == pytest.approx(500.0)
    assert beatToTimeMs(2.5, 100.0) == pytest.approx(1500.0)


def test_beat_to_time_ms_requires_positive_bpm():
    with pytest.raises(ValueError):
        beatToTimeMs(1.0, 0.0)

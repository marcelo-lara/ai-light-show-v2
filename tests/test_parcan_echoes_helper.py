from services.cue_helpers.parcan_echoes import generate_parcan_echoes


def test_generate_parcan_echoes_alternates_and_decays():
    entries = generate_parcan_echoes(
        120.0,
        {
            "start_time_ms": 1500,
            "color": "#00FFAA",
            "initial_value": 1.0,
            "delay_beats": 0.5,
            "flash_duration_beats": 0.25,
            "decay_factor": 0.5,
            "minimum_value": 0.2,
        },
    )

    assert [entry["fixture_id"] for entry in entries] == ["parcan_l", "parcan_r", "parcan_l"]
    assert [entry["time"] for entry in entries] == [1.5, 1.75, 2.0]
    assert all(entry["effect"] == "flash" for entry in entries)
    assert all(entry["duration"] == 0.125 for entry in entries)
    assert [entry["data"]["brightness"] for entry in entries] == [1.0, 0.5, 0.25]
    assert all(entry["data"]["color"] == "#00FFAA" for entry in entries)


def test_generate_parcan_echoes_rejects_invalid_decay_factor():
    try:
        generate_parcan_echoes(120.0, {"decay_factor": 1.0})
    except ValueError as exc:
        assert str(exc) == "decay_factor_out_of_range"
        return
    raise AssertionError("expected decay_factor_out_of_range")
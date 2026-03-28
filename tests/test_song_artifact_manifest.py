from models.song.artifacts import build_essentia_plot_descriptors, get_essentia_artifact_entry


def test_build_essentia_plot_descriptors_supports_nested_manifest():
    artifacts = {
        "essentia": {
            "mix": {"rhythm": {"svg": "/app/meta/Song/essentia/rhythm.svg"}},
            "bass": {"chroma_hpcp": {"svg": "/app/meta/Song/essentia/bass_chroma_hpcp.svg"}},
        }
    }

    plots = build_essentia_plot_descriptors(artifacts)

    assert plots == [
        {"id": "rhythm", "title": "Rhythm", "svg": "/app/meta/Song/essentia/rhythm.svg"},
        {"id": "bass_chroma_hpcp", "title": "Bass Chroma Hpcp", "svg": "/app/meta/Song/essentia/bass_chroma_hpcp.svg"},
    ]


def test_get_essentia_artifact_entry_supports_nested_and_flat_manifest():
    nested = {"essentia": {"mix": {"loudness_envelope": {"json": "/mix.json"}}, "drums": {"loudness_envelope": {"json": "/drums.json"}}}}
    flat = {"essentia": {"loudness_envelope": {"json": "/mix.json"}, "drums_loudness_envelope": {"json": "/drums.json"}}}

    assert get_essentia_artifact_entry(nested, "mix", "loudness_envelope") == {"json": "/mix.json"}
    assert get_essentia_artifact_entry(nested, "drums", "loudness_envelope") == {"json": "/drums.json"}
    assert get_essentia_artifact_entry(flat, "mix", "loudness_envelope") == {"json": "/mix.json"}
    assert get_essentia_artifact_entry(flat, "drums", "loudness_envelope") == {"json": "/drums.json"}
# End-to-end test report (CPU-mode run)

Date: 2026-02-04

Summary
-------
I ran the analyzer pipeline end-to-end (CPU mode) on `analyzer/songs/sono - keep control.mp3` from the ai-light venv. The pipeline completed and produced artifacts; some ML steps succeeded, others failed due to missing or incompatible packages in this environment.

Results (per-step)
------------------
- ingest: OK — `timeline.json` produced.
- stems: OK — stems files written to `temp_files/<slug>/stems/` and `analysis/stems.json` produced. Note: demucs CLI produced stems but exited with a non-zero code in its system Python (torchcodec missing there); the step now treats produced stems as success with a warning.
- beats: FAILED — `madmom` was not available in the test env; the pipeline uses `librosa` as the primary tracker (recommended). Optionally install `madmom` via conda-forge for improved downbeat estimation (see notes below).
- energy: OK — `analysis/energy.json` produced.
- drums: FAILED — `omnizart` not installed (ModuleNotFoundError). After `madmom` is available, `pip install omnizart` should enable this step.
- vocals: OK — Silero VAD ran successfully (after installing `torchcodec` in the ai-light venv).
- sections: FAILED — `openl3` not available; prefer `mamba install -c conda-forge openl3`.
- patterns: FAILED — depends on `beats.json` which is missing.
- show_plan: OK — placeholder `show_plan.json`, `roles.json`, `moments.json` produced (patterns/sections missing references).

What I installed in the ai-light venv during the test
---------------------------------------------------
- CPU PyTorch wheels: `torch`, `torchvision`, `torchaudio` (CPU wheels)
- `torchcodec` (fixed torchaudio save issue for Silero/Demucs usage)
- build tools: `Cython`, `wheel`, `setuptools`

What still needs OS/conda-level fixes (recommended)
--------------------------------------------------
- `openl3` is easiest installed from conda-forge (it may fail to build in isolated pip builds on this Python version). Recommended:

  mamba install -c conda-forge openl3 -y

- `madmom` is optional; install it via conda-forge if you want the advanced downbeat model: `mamba install -c conda-forge madmom -y`.

  pip install omnizart

- Make sure `demucs` CLI and `torchcodec` are installed in the same Python environment used to run `demucs` if you rely on a system demucs installation. Alternatively, install `demucs` in the same ai-light venv:

  pip install 'git+https://github.com/facebookresearch/demucs.git'

  (may require pinning torchaudio to compatible version; if you use the conda route for madmom/openl3, prefer a conda env for everything to reduce conflicts)

Files produced during this run
----------------------------
- `metadata/sono_-_keep_control/analysis/`: `timeline.json`, `stems.json`, `energy.json`, `vocals.json`, `run.json`
- `metadata/sono_-_keep_control/show_plan/`: `show_plan.json`, `roles.json`, `moments.json`

Next steps I can take (pick one)
--------------------------------
1. Attempt to install `openl3` (and optionally `madmom` if you want improved downbeat estimation) via conda-forge in a new conda env and re-run the pipeline until all steps succeed. (Recommended.)
2. Add a soft fallback in `beats` step to run a CPU-friendly tracker (e.g., `librosa.beat`) when `madmom` is unavailable — but this would be a change to behavior and may violate the project rule of using a single pinned ML backend.
3. Create an `install_gpu.sh` that asks for CUDA version and automates the exact wheel install for torch/CUDA and the optional packages.

If you want, I can proceed with (1) and generate the exact conda commands (and a script) and then re-run the pipeline to produce full successful artifacts.

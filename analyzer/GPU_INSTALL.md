# Install instructions for a GPU-capable analyzer environment (exact commands)

This document contains exact commands to prepare a GPU-capable environment for the analyzer pipeline. Pick the commands that match your system (conda/mamba is recommended for CUDA toolchain management).

---

## 1) Create a conda environment (recommended)

# Example: with mamba (fast)
mamba create -n ai-light-gpu python=3.11 -y
mamba activate ai-light-gpu

# Install CUDA-enabled PyTorch (pick the command matching your CUDA driver)
# For CUDA 12.1 (recommended if you have 12.x driver):
pip install --index-url https://download.pytorch.org/whl/cu121 torch torchvision torchaudio --upgrade

# For CUDA 11.8:
# pip install --index-url https://download.pytorch.org/whl/cu118 torch torchvision torchaudio --upgrade

# Verify torch + cuda
python -c "import torch; print(torch.__version__); print(torch.cuda.is_available()); print(torch.version.cuda)"

# Install the analyzer optional ML deps
pip install -r analyzer/requirements-ml.txt
pip install -r analyzer/requirements-drums.txt

# Install demucs CLI (if not installed via pip above)
pip install demucs

# (Optional) install omnizart extras for drum transcription
pip install omnizart

---

## 2) Using a system venv (pip)

# Create venv
python -m venv ~/.venvs/ai-light-gpu
source ~/.venvs/ai-light-gpu/bin/activate

# Install CUDA-enabled torch (choose the correct wheel)
pip install --index-url https://download.pytorch.org/whl/cu121 torch torchvision torchaudio --upgrade

# Then install analyzer ml deps
pip install -r analyzer/requirements-ml.txt
pip install -r analyzer/requirements-drums.txt
pip install demucs omnizart

---

## 3) Notes and troubleshooting
- Match the PyTorch wheel to your system CUDA driver (use `nvidia-smi` to see driver version). Installing a wheel with an unsupported CUDA version may still work if the driver is newer, but best practice is alignment.
- If you don't have a GPU or prefer CPU-only, install CPU wheels (omit the `--index-url` and install `torch` normally or use `pip install torch --index-url https://download.pytorch.org/whl/cpu`).
- Demucs benefits strongly from GPU when using large models.
- After installing, run one of the quick checks in this repo to confirm models can be imported.

---

## 4) Quick verification commands to run after installation

# Check demucs availability
python -c "import subprocess, sys
try:
    subprocess.check_call(['demucs','--help'])
    print('demucs_ok')
except Exception as e:
    print('demucs_missing', e)
"

# Check omnizart import
python -c "import omnizart; print('omnizart', omnizart.__version__)"

# Check openl3 import
python -c "import openl3; print('openl3', openl3.__version__)"

# Run the pipeline (from analyzer/ folder)
python -m song_analyzer analyze songs/'sono - keep control.mp3' --device cuda --out metadata/ --temp temp_files/ --stems-model demucs:htdemucs_ft

---

### Additional notes for installing `openl3`, `omnizart`, and optional `madmom`

Some packages (notably `openl3`) are easiest to install from conda-forge because they require compiled C extensions or older build-time toolchains that can fail on newer Python/pip isolation. `madmom` is optional and provides a high-quality downbeat model if you want improved downbeat detection.

# Using mamba/conda (recommended for these packages)
mamba install -c conda-forge openl3 -y

# If you want the optional downbeat model (madmom), install it as well:
# mamba install -c conda-forge madmom -y

# Then install omnizart (pip), which may depend on madmom
pip install omnizart

# If you prefer pip-only and encounter build issues, try python 3.10 in a venv or use the conda approach above.

If you want, I can generate a single `install_gpu.sh` script tuned to your driver version — tell me your CUDA version (or run `nvidia-smi`).

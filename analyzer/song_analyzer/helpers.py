# %%
# Setup

import os
import json
import matplotlib.pyplot as plt
import librosa
import librosa.display
# Plot stems waveforms
TMP_FILES = "/home/darkangel/ai-light-show-v2/analyzer/temp_files"
SONG_FOLDER = "sono_-_keep_control"
STEMS_PATH = os.path.join(TMP_FILES, SONG_FOLDER, "stems")
STEMS = ["bass", "drums", "vocals", "other"]
DATA_PATH = "/home/darkangel/ai-light-show-v2/backend/metadata/sono_keep_control/sono_-_keep_control"
AUDIO_PATH = "/home/darkangel/ai-light-show-v2/backend/songs/sono - keep control.mp3"
SECTIONS = "analysis/sections.json"
VOCALS = "analysis/vocals.json"
MOMENTS = "show_plan/moments.json"

# %%
# Song Sections

def generate_waveform_plot(y, sr, sections_path, output_path):
    # Load sections
    with open(sections_path, 'r') as f:
        data = json.load(f)
        sections = data.get('sections', [])
    
    # Plot waveform
    plt.figure(figsize=(12, 4))
    librosa.display.waveshow(y, sr=sr)
    plt.xlabel('Time (seconds)')
    plt.ylabel('Amplitude')
    plt.title('Section Boundaries')
    
    # Add vertical lines for section boundaries
    for i, section in enumerate(sections):
        start = section.get('start_s', 0)
        label = section.get('label', f'Section {i}')
        plt.axvline(x=start, color='red', linestyle='--', linewidth=1)
        # Add label above the line
        plt.text(start, 0.9, label, rotation=90, verticalalignment='bottom', fontsize=8, transform=plt.gca().transData)
    
    # Save the plot
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.tight_layout()
    plt.savefig(output_path, format='svg')
    plt.close()

# %%
# Render vocals phrases
def generate_vocals_waveform_plot(y, sr, vocals_path, output_path):
    # Load vocals phrases
    with open(vocals_path, 'r') as f:
        data = json.load(f)
        phrases = data.get('phrases', [])
    
    # Plot waveform
    plt.figure(figsize=(12, 4))
    librosa.display.waveshow(y, sr=sr)
    plt.xlabel('Time (seconds)')
    plt.ylabel('Amplitude')
    plt.title('Vocal Phrases')
    
    # Highlight vocal phrases
    for phrase in phrases:
        start = phrase.get('start_s', 0)
        end = phrase.get('end_s', 0)
        plt.axvspan(start, end, color='yellow', alpha=0.5)
    
    # Save the plot
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.tight_layout()
    plt.savefig(output_path, format='svg')
    plt.close()

# %% Render moments waveform
def generate_moments_waveform_plot(y, sr, moments_path, output_path):
    # Load moments
    with open(moments_path, 'r') as f:
        data = json.load(f)
        moments = data.get('moments', [])
    
    # Plot waveform
    plt.figure(figsize=(12, 4))
    librosa.display.waveshow(y, sr=sr)
    plt.xlabel('Time (seconds)')
    plt.ylabel('Amplitude')
    plt.title('Show Moments')
    
    # Highlight moments
    for moment in moments:
        start = moment.get('time_s', 0)
        end = moment.get('time_s', 0)
        plt.axvspan(start, end, color='blue', alpha=0.5)
    
    # Save the plot
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.tight_layout()
    plt.savefig(output_path, format='svg')
    plt.close()

# %%
# Save the plot to DATA_PATH as svg

if __name__ == "__main__":
    # Load audio waveform
    y, sr = librosa.load(AUDIO_PATH)
    
    # Plot stems waveforms
    
    
    # Plot Inferences
    sections_path = os.path.join(DATA_PATH, SECTIONS)
    output_path = os.path.join(DATA_PATH, "plots/sections.svg")
    generate_waveform_plot(y, sr, sections_path, output_path)

    vocals_path = os.path.join(DATA_PATH, VOCALS)
    output_path = os.path.join(DATA_PATH, "plots/vocals.svg")
    generate_vocals_waveform_plot(y, sr, vocals_path, output_path)

    moments_path = os.path.join(DATA_PATH, MOMENTS)
    output_path = os.path.join(DATA_PATH, "plots/moments.svg")
    generate_moments_waveform_plot(y, sr, moments_path, output_path)

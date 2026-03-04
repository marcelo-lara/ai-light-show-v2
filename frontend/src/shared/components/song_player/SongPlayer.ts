import WaveSurfer from "wavesurfer.js";
import RegionsPlugin from "wavesurfer.js/dist/plugins/regions.esm.js";
import { getBackendStore } from "../../state/backend_state.ts";
import type { SongState } from "../../transport/protocol.ts";
import {
  transportJumpToTime,
  transportPause,
  transportPlay,
  transportStop,
} from "../../transport/transport_intents.ts";

type Section = {
  name: string;
  start_s: number;
  end_s: number;
};

class SongPlayerController {
  root: HTMLElement;

  private waveformEl: HTMLElement;
  private barBeatEl: HTMLElement;
  private positionEl: HTMLElement;
  private playPauseBtn: HTMLButtonElement;
  private zoomInput: HTMLInputElement;
  private showRegionsInput: HTMLInputElement;
  private showDownbeatsInput: HTMLInputElement;
  private songLabelEl: HTMLElement;

  private prevSectionBtn: HTMLButtonElement;
  private prevBeatBtn: HTMLButtonElement;
  private nextBeatBtn: HTMLButtonElement;
  private nextSectionBtn: HTMLButtonElement;
  private loopToggle: HTMLInputElement;

  private waveSurfer: any | null = null;
  private regionsPlugin: any | null = null;

  private currentSongKey = "";
  private sections: Section[] = [];
  private beats: number[] = [];
  private downbeats: number[] = [];
  private selectedSectionIndex: number | null = null;
  private implicitLoopSectionIndex: number | null = null;
  private durationMs = 0;
  private localTimeMs = 0;
  private isPlaying = false;

  private rafId: number | null = null;
  private syncTimerId: number | null = null;
  private seekSyncTimerId: number | null = null;
  private suppressSeekSync = false;

  constructor() {
    const root = document.createElement("section");
    root.className = "card song-player";

    const waveformWrap = document.createElement("div");
    waveformWrap.className = "song-player-waveform";

    const songLabel = document.createElement("div");
    songLabel.className = "song-player-title muted";
    songLabel.textContent = "No song loaded";

    const waveform = document.createElement("div");
    waveform.className = "song-player-wave";

    waveformWrap.append(songLabel, waveform);

    const controls = document.createElement("div");
    controls.className = "song-player-controls";

    const barBeat = document.createElement("div");
    barBeat.className = "song-player-barbeat mono";
    barBeat.textContent = "1.1";

    const transport = document.createElement("div");
    transport.className = "song-player-transport";

    const prevSection = this.button("Prev Section", () => this.jumpPrevSection());
    const prevBeat = this.button("Prev Beat", () => this.jumpPrevBeat());
    const stop = this.button("Stop", () => this.handleStop());
    const playPause = this.button("Play", () => this.togglePlayPause());
    const nextBeat = this.button("Next Beat", () => this.jumpNextBeat());
    const nextSection = this.button("Next Section", () => this.jumpNextSection());

    transport.append(prevSection, prevBeat, stop, playPause, nextBeat, nextSection);

    const options = document.createElement("div");
    options.className = "song-player-options";

    const loop = document.createElement("label");
    loop.className = "song-player-inline-toggle";
    const loopInput = document.createElement("input");
    loopInput.type = "checkbox";
    loopInput.addEventListener("change", () => {
      this.implicitLoopSectionIndex = null;
      if (loopInput.checked) {
        this.primeImplicitLoopFromCurrentTime();
      }
    });
    const loopText = document.createElement("span");
    loopText.textContent = "Loop Regions";
    loop.append(loopInput, loopText);

    const showRegions = document.createElement("label");
    showRegions.className = "song-player-inline-toggle";
    const showRegionsInput = document.createElement("input");
    showRegionsInput.type = "checkbox";
    showRegionsInput.checked = true;
    showRegionsInput.addEventListener("change", () => this.rebuildRegions());
    const showRegionsText = document.createElement("span");
    showRegionsText.textContent = "Show Sections";
    showRegions.append(showRegionsInput, showRegionsText);

    const showDownbeats = document.createElement("label");
    showDownbeats.className = "song-player-inline-toggle";
    const showDownbeatsInput = document.createElement("input");
    showDownbeatsInput.type = "checkbox";
    showDownbeatsInput.checked = true;
    showDownbeatsInput.addEventListener("change", () => this.rebuildRegions());
    const showDownbeatsText = document.createElement("span");
    showDownbeatsText.textContent = "Show Downbeats";
    showDownbeats.append(showDownbeatsInput, showDownbeatsText);

    const zoomWrap = document.createElement("label");
    zoomWrap.className = "song-player-zoom";
    const zoomText = document.createElement("span");
    zoomText.textContent = "Zoom";
    const zoomInput = document.createElement("input");
    zoomInput.type = "range";
    zoomInput.min = "10";
    zoomInput.max = "180";
    zoomInput.step = "10";
    zoomInput.value = "40";
    zoomInput.addEventListener("input", () => {
      if (!this.waveSurfer) return;
      this.waveSurfer.zoom(Number(zoomInput.value));
    });
    zoomWrap.append(zoomText, zoomInput);

    options.append(loop, showRegions, showDownbeats, zoomWrap);

    const position = document.createElement("div");
    position.className = "song-player-position mono muted";
    position.textContent = "0:00 / 0:00";

    controls.append(barBeat, transport, options, position);
    root.append(waveformWrap, controls);

    this.root = root;
    this.waveformEl = waveform;
    this.barBeatEl = barBeat;
    this.positionEl = position;
    this.playPauseBtn = playPause;
    this.zoomInput = zoomInput;
    this.showRegionsInput = showRegionsInput;
    this.showDownbeatsInput = showDownbeatsInput;
    this.songLabelEl = songLabel;

    this.prevSectionBtn = prevSection;
    this.prevBeatBtn = prevBeat;
    this.nextBeatBtn = nextBeat;
    this.nextSectionBtn = nextSection;
    this.loopToggle = loopInput;

    this.updateControlAvailability();
  }

  refreshFromStore() {
    const state = getBackendStore().state;
    const song = state.song ?? null;
    const playback = state.playback ?? {};

    if (song) {
      const nextKey = `${song.filename ?? ""}|${song.audio_url ?? ""}`;
      if (this.currentSongKey !== nextKey) {
        this.currentSongKey = nextKey;
        this.selectedSectionIndex = null;
        this.implicitLoopSectionIndex = null;
        this.loadSong(song);
      } else {
        this.applySongData(song);
      }
    } else {
      this.currentSongKey = "";
      this.songLabelEl.textContent = "No song loaded";
    }

    if (!this.isPlaying) {
      const backendTime = Number(playback.time_ms ?? 0);
      this.localTimeMs = Number.isFinite(backendTime) ? Math.max(0, backendTime) : 0;
      if (this.waveSurfer) {
        const seconds = this.localTimeMs / 1000;
        if (Math.abs(this.waveSurfer.getCurrentTime() - seconds) > 0.02) {
          this.suppressSeekSync = true;
          this.waveSurfer.setTime(seconds);
          this.suppressSeekSync = false;
        }
      }
      this.renderReadout();
    }

    this.playPauseBtn.textContent = this.isPlaying ? "Pause" : "Play";
    this.updateControlAvailability();
  }

  private updateControlAvailability() {
    const hasSections = this.sections.length > 0;
    const hasBeats = this.beats.length > 0;
    const hasWave = !!this.waveSurfer;

    this.prevSectionBtn.disabled = !hasSections || !hasWave;
    this.prevSectionBtn.title = hasSections ? "Jump to previous section start" : "No section metadata available";

    this.nextSectionBtn.disabled = !hasSections || !hasWave;
    this.nextSectionBtn.title = hasSections ? "Jump to next section start" : "No section metadata available";

    this.prevBeatBtn.disabled = !hasBeats || !hasWave;
    this.prevBeatBtn.title = hasBeats ? "Jump to previous beat" : "No beat metadata available";

    this.nextBeatBtn.disabled = !hasBeats || !hasWave;
    this.nextBeatBtn.title = hasBeats ? "Jump to next beat" : "No beat metadata available";

    this.loopToggle.disabled = !hasSections;
    this.loopToggle.title = hasSections
      ? "Loop within selected section, or capture and loop the next section when none is selected"
      : "No sections available for loop regions";
  }

  private button(label: string, onClick: () => void): HTMLButtonElement {
    const btn = document.createElement("button");
    btn.className = "btn";
    btn.textContent = label;
    btn.addEventListener("click", onClick);
    return btn;
  }

  private async togglePlayPause() {
    if (!this.waveSurfer) return;

    if (this.isPlaying) {
      this.waveSurfer.pause();
      this.isPlaying = false;
      this.playPauseBtn.textContent = "Play";
      transportPause();
      this.syncTimecodeNow();
      this.stopTimers();
      return;
    }

    try {
      await this.waveSurfer.play();
      this.isPlaying = true;
      this.playPauseBtn.textContent = "Pause";
      transportPlay();
      this.syncTimecodeNow();
      this.startTimers();
    } catch {
      this.isPlaying = false;
      this.playPauseBtn.textContent = "Play";
    }
  }

  private handleStop() {
    if (!this.waveSurfer) return;

    this.waveSurfer.pause();
    this.waveSurfer.setTime(0);
    this.isPlaying = false;
    this.localTimeMs = 0;
    this.renderReadout();
    this.playPauseBtn.textContent = "Play";
    transportStop();
    this.syncTimecodeNow();
    this.stopTimers();
    this.implicitLoopSectionIndex = null;
  }

  private jumpPrevBeat() {
    if (!this.waveSurfer || this.beats.length === 0) return;
    const t = this.localTimeMs / 1000;
    let target = 0;
    for (const beat of this.beats) {
      if (beat >= t - 0.01) break;
      target = beat;
    }
    this.seekToTimeMs(Math.round(target * 1000));
  }

  private jumpNextBeat() {
    if (!this.waveSurfer || this.beats.length === 0) return;
    const t = this.localTimeMs / 1000;
    const lastBeat = this.beats[this.beats.length - 1] ?? 0;
    let target = lastBeat;
    for (const beat of this.beats) {
      if (beat > t + 0.01) {
        target = beat;
        break;
      }
    }
    this.seekToTimeMs(Math.round(target * 1000));
  }

  private jumpPrevSection() {
    if (!this.waveSurfer || this.sections.length === 0) return;
    const t = this.localTimeMs / 1000;
    const current = this.findCurrentSectionIndex(t);
    let targetIndex: number;

    if (current === null) {
      let before = -1;
      for (let idx = 0; idx < this.sections.length; idx++) {
        if (this.sections[idx].start_s < t - 0.01) before = idx;
      }
      targetIndex = before;
    } else {
      targetIndex = current - 1;
    }

    if (targetIndex < 0) {
      this.selectedSectionIndex = null;
      this.seekToTimeMs(0);
      return;
    }

    this.selectedSectionIndex = targetIndex;
    this.implicitLoopSectionIndex = null;
    this.seekToTimeMs(Math.round(this.sections[targetIndex].start_s * 1000));
    this.rebuildRegions();
  }

  private jumpNextSection() {
    if (!this.waveSurfer || this.sections.length === 0) return;
    const t = this.localTimeMs / 1000;
    const current = this.findCurrentSectionIndex(t);

    let targetIndex = this.sections.length - 1;
    if (current === null) {
      for (let idx = 0; idx < this.sections.length; idx++) {
        if (this.sections[idx].start_s > t + 0.01) {
          targetIndex = idx;
          break;
        }
      }
    } else if (current < this.sections.length - 1) {
      targetIndex = current + 1;
    }

    this.selectedSectionIndex = targetIndex;
    this.implicitLoopSectionIndex = null;
    this.seekToTimeMs(Math.round(this.sections[targetIndex].start_s * 1000));
    this.rebuildRegions();
  }

  private seekToTimeMs(targetMs: number) {
    if (!this.waveSurfer) return;
    const clamped = Math.max(0, Math.min(targetMs, this.durationMs || targetMs));
    this.localTimeMs = clamped;
    this.suppressSeekSync = true;
    this.waveSurfer.setTime(clamped / 1000);
    this.suppressSeekSync = false;
    this.renderReadout();
    this.syncTimecodeNow();
  }

  private findCurrentSectionIndex(t: number): number | null {
    for (let idx = 0; idx < this.sections.length; idx++) {
      const section = this.sections[idx];
      if (section.start_s <= t && t < section.end_s) {
        return idx;
      }
    }
    return null;
  }

  private primeImplicitLoopFromCurrentTime() {
    if (!this.loopToggle.checked || this.selectedSectionIndex !== null) return;
    const t = this.localTimeMs / 1000;
    this.implicitLoopSectionIndex = null;
    for (let idx = 0; idx < this.sections.length; idx++) {
      if (this.sections[idx].start_s > t + 0.001) {
        this.implicitLoopSectionIndex = idx;
        break;
      }
    }
  }

  private enforceLoopRules() {
    if (!this.waveSurfer || !this.loopToggle.checked || this.sections.length === 0) return;

    let targetIndex = this.selectedSectionIndex;

    if (targetIndex === null) {
      if (this.implicitLoopSectionIndex === null) {
        this.primeImplicitLoopFromCurrentTime();
      }
      targetIndex = this.implicitLoopSectionIndex;
      if (targetIndex === null) {
        return;
      }

      const target = this.sections[targetIndex];
      if (this.localTimeMs / 1000 < target.start_s) {
        return;
      }
    }

    const section = this.sections[targetIndex];
    const t = this.localTimeMs / 1000;
    const endGuard = section.end_s - 0.012;
    if (t >= endGuard) {
      this.seekToTimeMs(Math.round(section.start_s * 1000));
    }
  }

  private ensureWaveSurfer() {
    if (this.waveSurfer) return;

    this.waveSurfer = WaveSurfer.create({
      container: this.waveformEl,
      waveColor: "var(--accent)",
      progressColor: "var(--accent-2)",
      cursorColor: "var(--text)",
      height: 110,
      normalize: true,
      dragToSeek: true,
    });

    this.regionsPlugin = this.waveSurfer.registerPlugin(RegionsPlugin.create());

    this.waveSurfer.on("ready", (durationSec: number) => {
      this.durationMs = Math.max(0, Math.round(Number(durationSec || 0) * 1000));
      this.renderReadout();
      this.rebuildRegions();
    });

    this.waveSurfer.on("timeupdate", (seconds: number) => {
      this.localTimeMs = Math.max(0, Math.round(Number(seconds || 0) * 1000));
      this.renderReadout();
      this.enforceLoopRules();
    });

    this.waveSurfer.on("seeking", (seconds: number) => {
      this.localTimeMs = Math.max(0, Math.round(Number(seconds || 0) * 1000));
      this.renderReadout();
      if (this.suppressSeekSync) return;
      if (this.seekSyncTimerId !== null) {
        clearTimeout(this.seekSyncTimerId);
      }
      this.seekSyncTimerId = window.setTimeout(() => {
        this.seekSyncTimerId = null;
        this.syncTimecodeNow();
      }, 120);
    });

    this.waveSurfer.on("finish", () => {
      this.isPlaying = false;
      this.playPauseBtn.textContent = "Play";
      this.stopTimers();
      this.syncTimecodeNow();
    });

    this.waveSurfer.on("pause", () => {
      if (!this.isPlaying) return;
      this.isPlaying = false;
      this.playPauseBtn.textContent = "Play";
      this.stopTimers();
      this.syncTimecodeNow();
    });

    this.waveSurfer.on("play", () => {
      this.isPlaying = true;
      this.playPauseBtn.textContent = "Pause";
      if (this.loopToggle.checked && this.selectedSectionIndex === null) {
        this.primeImplicitLoopFromCurrentTime();
      }
      this.startTimers();
    });

    this.waveSurfer.zoom(Number(this.zoomInput.value));
    this.updateControlAvailability();
  }

  private loadSong(song: SongState) {
    this.applySongData(song);

    const audioUrl = this.resolveAudioUrl(song.audio_url ?? null);
    if (!audioUrl) {
      this.songLabelEl.textContent = `${song.filename ?? "No song"} (missing audio URL)`;
      return;
    }

    this.ensureWaveSurfer();
    this.waveSurfer.load(audioUrl);
  }

  private applySongData(song: SongState) {
    this.songLabelEl.textContent = song.filename ? `Song: ${song.filename}` : "Song loaded";

    const parts = Array.isArray(song.sections) ? song.sections : [];
    this.sections = parts
      .map((section) => ({
        name: String(section.name ?? "Section"),
        start_s: Number(section.start_s ?? 0),
        end_s: Number(section.end_s ?? 0),
      }))
      .filter((section) => Number.isFinite(section.start_s) && Number.isFinite(section.end_s) && section.end_s > section.start_s)
      .sort((a, b) => a.start_s - b.start_s);

    if (this.selectedSectionIndex !== null && this.selectedSectionIndex >= this.sections.length) {
      this.selectedSectionIndex = null;
    }
    if (this.implicitLoopSectionIndex !== null && this.implicitLoopSectionIndex >= this.sections.length) {
      this.implicitLoopSectionIndex = null;
    }

    this.beats = this.cleanSortedNumeric(song.beats);
    this.downbeats = this.cleanSortedNumeric(song.downbeats);

    const lengthMs = Number(song.length_s ?? 0) * 1000;
    if (Number.isFinite(lengthMs) && lengthMs > 0) {
      this.durationMs = Math.max(this.durationMs, Math.round(lengthMs));
    }

    this.rebuildRegions();
    this.renderReadout();
    this.updateControlAvailability();
  }

  private cleanSortedNumeric(values: unknown): number[] {
    if (!Array.isArray(values)) return [];
    return values
      .map((value) => Number(value))
      .filter((value) => Number.isFinite(value) && value >= 0)
      .sort((a, b) => a - b);
  }

  private rebuildRegions() {
    if (!this.regionsPlugin) return;

    this.regionsPlugin.clearRegions();

    if (this.showRegionsInput.checked) {
      for (let idx = 0; idx < this.sections.length; idx++) {
        const section = this.sections[idx];
        const selected = idx === this.selectedSectionIndex;
        const region = this.regionsPlugin.addRegion({
          start: section.start_s,
          end: section.end_s,
          content: section.name,
          color: selected
            ? "color-mix(in oklab, var(--accent-2) 35%, transparent)"
            : "color-mix(in oklab, var(--accent) 25%, transparent)",
          drag: false,
          resize: false,
        });

        region.on?.("click", (event: Event) => {
          event.preventDefault();
          event.stopPropagation();
          this.selectedSectionIndex = idx;
          this.implicitLoopSectionIndex = null;
          this.rebuildRegions();
        });
      }
    }

    if (this.showDownbeatsInput.checked) {
      for (const downbeat of this.downbeats) {
        this.regionsPlugin.addRegion({
          start: downbeat,
          end: downbeat + 0.015,
          color: "color-mix(in oklab, var(--text) 45%, transparent)",
          drag: false,
          resize: false,
        });
      }
    }
  }

  private startTimers() {
    this.stopTimers();

    this.syncTimerId = window.setInterval(() => {
      if (!this.isPlaying) return;
      this.syncTimecodeNow();
    }, 10_000);

    const tick = () => {
      if (!this.isPlaying || !this.waveSurfer) {
        this.rafId = null;
        return;
      }
      this.localTimeMs = Math.max(0, Math.round(this.waveSurfer.getCurrentTime() * 1000));
      this.renderReadout();
      this.rafId = requestAnimationFrame(tick);
    };

    this.rafId = requestAnimationFrame(tick);
  }

  private stopTimers() {
    if (this.syncTimerId !== null) {
      clearInterval(this.syncTimerId);
      this.syncTimerId = null;
    }
    if (this.seekSyncTimerId !== null) {
      clearTimeout(this.seekSyncTimerId);
      this.seekSyncTimerId = null;
    }
    if (this.rafId !== null) {
      cancelAnimationFrame(this.rafId);
      this.rafId = null;
    }
  }

  private syncTimecodeNow() {
    transportJumpToTime(this.localTimeMs);
  }

  private renderReadout() {
    this.positionEl.textContent = `${formatMs(this.localTimeMs)} / ${formatMs(this.durationMs)}`;
    this.barBeatEl.textContent = this.computeBarBeatLabel();
  }

  private computeBarBeatLabel(): string {
    if (!this.downbeats.length) return "1.1";

    const t = this.localTimeMs / 1000;
    let barIndex = 0;
    for (let idx = 0; idx < this.downbeats.length; idx++) {
      if (this.downbeats[idx] <= t) barIndex = idx;
      else break;
    }

    const barStart = this.downbeats[barIndex] ?? 0;
    let beatIndex = 1;
    for (const beat of this.beats) {
      if (beat > barStart && beat <= t + 0.0005) {
        beatIndex += 1;
      }
      if (beat > t) break;
    }

    return `${barIndex + 1}.${Math.min(9, Math.max(1, beatIndex))}`;
  }

  private resolveAudioUrl(rawUrl: string | null): string | null {
    if (!rawUrl) return null;
    if (rawUrl.startsWith("http://") || rawUrl.startsWith("https://")) return rawUrl;

    const origin = String((globalThis as any).__BACKEND_HTTP_ORIGIN__ ?? "").trim();
    if (rawUrl.startsWith("/") && origin) {
      return `${origin}${rawUrl}`;
    }

    return rawUrl;
  }
}

let singleton: SongPlayerController | null = null;

export function SongPlayer(): HTMLElement {
  if (!singleton) {
    singleton = new SongPlayerController();
  }
  singleton.refreshFromStore();
  return singleton.root;
}

function formatMs(value: number): string {
  const total = Math.max(0, Math.floor(value / 1000));
  const minutes = Math.floor(total / 60);
  const seconds = String(total % 60).padStart(2, "0");
  return `${minutes}:${seconds}`;
}

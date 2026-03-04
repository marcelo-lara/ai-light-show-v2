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
import { formatMs } from "./logic/time.ts";
import type { Section } from "./types/types.ts";
import {
  cleanSortedNumeric,
  computeBarBeatLabel,
  getImplicitLoopSectionIndex,
  getNextBeatTimeMs,
  getNextSectionTargetIndex,
  getPrevBeatTimeMs,
  getPrevSectionTargetIndex,
  normalizeSections,
  songFingerprint,
} from "./logic/song_logic.ts";
import { rebuildSongRegions } from "./logic/regions.ts";
import { Waveform } from "./ui/Waveform.ts";
import { TransportControls } from "./ui/TransportControls.ts";
import { PlaybackReadout } from "./ui/PlaybackReadout.ts";
import { PlayerOptions, ZoomControl } from "./ui/PlayerOptions.ts";
import { Layout } from "./ui/Layout.ts";

export class SongPlayerController {
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
  private hasAudioLoaded = false;
  private songMetaFingerprint = "";

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
  private appliedZoomValue: number | null = null;

  constructor() {
    const { container: waveformContainer, wave: waveform, title: songLabel } = Waveform();
    const {
      container: transportContainer,
      prevSectionBtn,
      prevBeatBtn,
      stopBtn,
      playPauseBtn,
      nextBeatBtn,
      nextSectionBtn,
    } = TransportControls({
      onPrevSection: () => this.jumpPrevSection(),
      onPrevBeat: () => this.jumpPrevBeat(),
      onStop: () => this.handleStop(),
      onPlayPause: () => this.togglePlayPause(),
      onNextBeat: () => this.jumpNextBeat(),
      onNextSection: () => this.jumpNextSection(),
    });

    const { barBeatEl, positionEl } = PlaybackReadout();

    const {
      container: optionsContainer,
      loopToggle,
      showSectionsToggle,
      showDownbeatsToggle,
    } = PlayerOptions({
      onLoopToggle: (checked) => {
        this.implicitLoopSectionIndex = null;
        if (checked) {
          this.primeImplicitLoopFromCurrentTime();
        }
      },
      onShowSectionsToggle: () => this.rebuildRegions(),
      onShowDownbeatsToggle: () => this.rebuildRegions(),
    });

    const { container: zoomContainer, zoomSlider } = ZoomControl({
      initialZoom: 40,
      onZoom: () => this.applyZoom(),
    });

    this.root = Layout({
      waveform: waveformContainer,
      barBeat: barBeatEl,
      transport: transportContainer,
      options: optionsContainer,
      zoom: zoomContainer,
      position: positionEl,
    });

    this.waveformEl = waveform;
    this.barBeatEl = barBeatEl;
    this.positionEl = positionEl;
    this.playPauseBtn = playPauseBtn;
    this.zoomInput = zoomSlider;
    this.showRegionsInput = showSectionsToggle;
    this.showDownbeatsInput = showDownbeatsToggle;
    this.songLabelEl = songLabel;

    this.prevSectionBtn = prevSectionBtn;
    this.prevBeatBtn = prevBeatBtn;
    this.nextBeatBtn = nextBeatBtn;
    this.nextSectionBtn = nextSectionBtn;
    this.loopToggle = loopToggle;

    this.updateControlAvailability();
  }

  refreshFromStore() {
    const state = getBackendStore().state;
    const song = state.song ?? null;
    const playback = state.playback ?? {};

    if (song) {
      const nextKey = `${song.filename ?? ""}|${song.audio_url ?? ""}`;
      const nextFingerprint = songFingerprint(song);
      if (this.currentSongKey !== nextKey) {
        this.currentSongKey = nextKey;
        this.songMetaFingerprint = nextFingerprint;
        this.selectedSectionIndex = null;
        this.implicitLoopSectionIndex = null;
        this.loadSong(song);
      } else if (this.songMetaFingerprint !== nextFingerprint) {
        this.songMetaFingerprint = nextFingerprint;
        this.applySongData(song);
      }
    } else {
      this.currentSongKey = "";
      this.songMetaFingerprint = "";
      this.songLabelEl.textContent = "No song loaded";
    }

    if (!this.isPlaying) {
      const backendTime = Number(playback.time_ms ?? 0);
      this.localTimeMs = Number.isFinite(backendTime) ? Math.max(0, backendTime) : 0;
      if (this.waveSurfer && this.hasAudioLoaded) {
        const seconds = this.localTimeMs / 1000;
        if (Math.abs(this.safeGetCurrentTime() - seconds) > 0.02) {
          this.suppressSeekSync = true;
          this.safeSetTime(seconds);
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

  private async togglePlayPause() {
    if (!this.waveSurfer || !this.hasAudioLoaded) return;

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
    if (this.hasAudioLoaded) {
      this.safeSetTime(0);
    }
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
    this.seekToTimeMs(getPrevBeatTimeMs(this.beats, this.localTimeMs));
  }

  private jumpNextBeat() {
    if (!this.waveSurfer || this.beats.length === 0) return;
    this.seekToTimeMs(getNextBeatTimeMs(this.beats, this.localTimeMs));
  }

  private jumpPrevSection() {
    if (!this.waveSurfer || this.sections.length === 0) return;
    const targetIndex = getPrevSectionTargetIndex(this.sections, this.localTimeMs);

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
    const targetIndex = getNextSectionTargetIndex(this.sections, this.localTimeMs);

    this.selectedSectionIndex = targetIndex;
    this.implicitLoopSectionIndex = null;
    this.seekToTimeMs(Math.round(this.sections[targetIndex].start_s * 1000));
    this.rebuildRegions();
  }

  private seekToTimeMs(targetMs: number) {
    if (!this.waveSurfer) return;
    const clamped = Math.max(0, Math.min(targetMs, this.durationMs || targetMs));
    this.localTimeMs = clamped;
    if (this.hasAudioLoaded) {
      this.suppressSeekSync = true;
      this.safeSetTime(clamped / 1000);
      this.suppressSeekSync = false;
    }
    this.renderReadout();
    this.syncTimecodeNow();
  }

  private primeImplicitLoopFromCurrentTime() {
    if (!this.loopToggle.checked || this.selectedSectionIndex !== null) return;
    this.implicitLoopSectionIndex = getImplicitLoopSectionIndex(this.sections, this.localTimeMs);
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
      hideScrollbar: false,
      fillParent: true,
      width: "100%",
      minPxPerSec: 50,
      normalize: true,
      dragToSeek: true,
    });

    this.regionsPlugin = this.waveSurfer.registerPlugin(RegionsPlugin.create());

    this.waveSurfer.on("ready", (durationSec: number) => {
      this.hasAudioLoaded = true;
      this.durationMs = Math.max(0, Math.round(Number(durationSec || 0) * 1000));
      this.appliedZoomValue = null;
      this.renderReadout();
      this.rebuildRegions();
    });

    this.waveSurfer.on("error", () => {
      this.hasAudioLoaded = false;
      this.isPlaying = false;
      this.playPauseBtn.textContent = "Play";
      this.stopTimers();
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
    this.hasAudioLoaded = false;
    this.waveSurfer.load(audioUrl);
  }

  private applySongData(song: SongState) {
    this.songLabelEl.textContent = song.filename ? `Song: ${song.filename}` : "Song loaded";

    this.sections = normalizeSections(song.sections);

    if (this.selectedSectionIndex !== null && this.selectedSectionIndex >= this.sections.length) {
      this.selectedSectionIndex = null;
    }
    if (this.implicitLoopSectionIndex !== null && this.implicitLoopSectionIndex >= this.sections.length) {
      this.implicitLoopSectionIndex = null;
    }

    this.beats = cleanSortedNumeric(song.beats);
    this.downbeats = cleanSortedNumeric(song.downbeats);

    const lengthMs = Number(song.length_s ?? 0) * 1000;
    if (Number.isFinite(lengthMs) && lengthMs > 0) {
      this.durationMs = Math.max(this.durationMs, Math.round(lengthMs));
    }

    this.rebuildRegions();
    this.renderReadout();
    this.updateControlAvailability();
  }

  private rebuildRegions() {
    rebuildSongRegions({
      regionsPlugin: this.regionsPlugin,
      sections: this.sections,
      downbeats: this.downbeats,
      showSections: this.showRegionsInput.checked,
      showDownbeats: this.showDownbeatsInput.checked,
      selectedSectionIndex: this.selectedSectionIndex,
      onSelectSection: (index) => {
        this.selectedSectionIndex = index;
        this.implicitLoopSectionIndex = null;
        this.rebuildRegions();
      },
    });
  }

  private startTimers() {
    this.stopTimers();

    this.syncTimerId = window.setInterval(() => {
      if (!this.isPlaying) return;
      this.syncTimecodeNow();
    }, 10_000);

    const tick = () => {
      if (!this.isPlaying || !this.waveSurfer || !this.hasAudioLoaded) {
        this.rafId = null;
        return;
      }
      this.localTimeMs = Math.max(0, Math.round(this.safeGetCurrentTime() * 1000));
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

  private safeGetCurrentTime(): number {
    if (!this.waveSurfer || !this.hasAudioLoaded) return 0;
    try {
      return Number(this.waveSurfer.getCurrentTime() ?? 0);
    } catch {
      return 0;
    }
  }

  private safeSetTime(seconds: number) {
    if (!this.waveSurfer || !this.hasAudioLoaded) return;
    try {
      this.waveSurfer.setTime(seconds);
    } catch {
      // Ignore pre-ready setTime attempts.
    }
  }

  private applyZoom() {
    if (!this.waveSurfer || !this.hasAudioLoaded) return;

    const nextZoom = Number(this.zoomInput.value);
    if (!Number.isFinite(nextZoom)) return;
    if (this.appliedZoomValue === nextZoom) return;

    try {
      console.log("Applying zoom:", nextZoom);
      this.waveSurfer.zoom(nextZoom);
      this.appliedZoomValue = nextZoom;
    } catch {
      // Ignore pre-ready zoom attempts.
    }
  }

  private renderReadout() {
    this.positionEl.textContent = `${formatMs(this.localTimeMs)} / ${formatMs(this.durationMs)}`;
    this.barBeatEl.textContent = computeBarBeatLabel(this.downbeats, this.beats, this.localTimeMs);
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

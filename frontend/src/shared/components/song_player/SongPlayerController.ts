import { getBackendStore } from "../../state/backend_state.ts";
import type { SongState } from "../../transport/protocol.ts";
import {
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
import { Waveform } from "./ui/Waveform.ts";
import { TransportControls } from "./ui/TransportControls.ts";
import { PlaybackReadout } from "./ui/PlaybackReadout.ts";
import { PlayerOptions, ZoomControl } from "./ui/PlayerOptions.ts";
import { Layout } from "./ui/Layout.ts";
import { WaveSurferManager } from "./logic/WaveSurferManager.ts";
import { PlaybackSync } from "./logic/PlaybackSync.ts";

export class SongPlayerController {
  root: HTMLElement;

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

  private waveSurferManager: WaveSurferManager;
  private playbackSync: PlaybackSync;

  private currentSongKey = "";
  private songMetaFingerprint = "";
  private sections: Section[] = [];
  private beats: number[] = [];
  private downbeats: number[] = [];
  private selectedSectionIndex: number | null = null;
  private implicitLoopSectionIndex: number | null = null;
  private durationMs = 0;
  private localTimeMs = 0;
  private isPlaying = false;

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

    this.waveSurferManager = new WaveSurferManager({
      container: waveform,
      onReady: (durationMs) => {
        this.durationMs = durationMs;
        this.appliedZoomValue = null;
        this.renderReadout();
        this.rebuildRegions();
      },
      onTimeUpdate: (seconds) => {
        this.localTimeMs = Math.max(0, Math.round(seconds * 1000));
        this.renderReadout();
        this.enforceLoopRules();
      },
      onSeeking: (seconds) => {
        this.localTimeMs = Math.max(0, Math.round(seconds * 1000));
        this.renderReadout();
        if (!this.suppressSeekSync) {
          this.playbackSync.debounceSeekSync(this.localTimeMs);
        }
      },
      onFinish: () => {
        this.isPlaying = false;
        this.playPauseBtn.textContent = "Play";
        this.playbackSync.stop();
        this.playbackSync.syncNow(this.localTimeMs);
      },
      onPlay: () => {
        this.isPlaying = true;
        this.playPauseBtn.textContent = "Pause";
        if (this.loopToggle.checked && this.selectedSectionIndex === null) {
          this.primeImplicitLoopFromCurrentTime();
        }
        this.playbackSync.start(() => this.waveSurferManager.getCurrentTime() * 1000);
      },
      onPause: () => {
        if (!this.isPlaying) return;
        this.isPlaying = false;
        this.playPauseBtn.textContent = "Play";
        this.playbackSync.stop();
        this.playbackSync.syncNow(this.localTimeMs);
      },
      onSelectSection: (index) => {
        this.selectedSectionIndex = index;
        this.implicitLoopSectionIndex = null;
        this.rebuildRegions();
      },
    });

    this.playbackSync = new PlaybackSync({
      onSync: (timeMs) => {
        this.localTimeMs = timeMs;
        this.renderReadout();
      },
    });

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
      if (this.waveSurferManager.isReady()) {
        const seconds = this.localTimeMs / 1000;
        if (Math.abs(this.waveSurferManager.getCurrentTime() - seconds) > 0.02) {
          this.suppressSeekSync = true;
          this.waveSurferManager.setTime(seconds);
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
    const hasWave = this.waveSurferManager?.isReady();

    this.prevSectionBtn.disabled = !hasSections || !hasWave;
    this.nextSectionBtn.disabled = !hasSections || !hasWave;
    this.prevBeatBtn.disabled = !hasBeats || !hasWave;
    this.nextBeatBtn.disabled = !hasBeats || !hasWave;
    this.loopToggle.disabled = !hasSections;
  }

  private async togglePlayPause() {
    if (!this.waveSurferManager.isReady()) return;

    if (this.isPlaying) {
      this.waveSurferManager.pause();
      transportPause();
      return;
    }

    try {
      await this.waveSurferManager.play();
      transportPlay();
    } catch {
      this.isPlaying = false;
      this.playPauseBtn.textContent = "Play";
    }
  }

  private handleStop() {
    this.waveSurferManager.pause();
    this.waveSurferManager.setTime(0);
    this.isPlaying = false;
    this.localTimeMs = 0;
    this.renderReadout();
    this.playPauseBtn.textContent = "Play";
    transportStop();
    this.playbackSync.syncNow(0);
    this.playbackSync.stop();
    this.implicitLoopSectionIndex = null;
  }

  private jumpPrevBeat() {
    this.seekToTimeMs(getPrevBeatTimeMs(this.beats, this.localTimeMs));
  }

  private jumpNextBeat() {
    this.seekToTimeMs(getNextBeatTimeMs(this.beats, this.localTimeMs));
  }

  private jumpPrevSection() {
    if (this.sections.length === 0) return;
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
    if (this.sections.length === 0) return;
    const targetIndex = getNextSectionTargetIndex(this.sections, this.localTimeMs);

    this.selectedSectionIndex = targetIndex;
    this.implicitLoopSectionIndex = null;
    this.seekToTimeMs(Math.round(this.sections[targetIndex].start_s * 1000));
    this.rebuildRegions();
  }

  private seekToTimeMs(targetMs: number) {
    const clamped = Math.max(0, Math.min(targetMs, this.durationMs || targetMs));
    this.localTimeMs = clamped;
    this.suppressSeekSync = true;
    this.waveSurferManager.setTime(clamped / 1000);
    this.suppressSeekSync = false;
    this.renderReadout();
    this.playbackSync.syncNow(this.localTimeMs);
  }

  private primeImplicitLoopFromCurrentTime() {
    if (!this.loopToggle.checked || this.selectedSectionIndex !== null) return;
    this.implicitLoopSectionIndex = getImplicitLoopSectionIndex(this.sections, this.localTimeMs);
  }

  private enforceLoopRules() {
    if (!this.loopToggle.checked || this.sections.length === 0) return;

    let targetIndex = this.selectedSectionIndex;

    if (targetIndex === null) {
      if (this.implicitLoopSectionIndex === null) {
        this.primeImplicitLoopFromCurrentTime();
      }
      targetIndex = this.implicitLoopSectionIndex;
      if (targetIndex === null) return;

      const target = this.sections[targetIndex];
      if (this.localTimeMs / 1000 < target.start_s) return;
    }

    const section = this.sections[targetIndex];
    const t = this.localTimeMs / 1000;
    const endGuard = section.end_s - 0.012;
    if (t >= endGuard) {
      this.seekToTimeMs(Math.round(section.start_s * 1000));
    }
  }

  private loadSong(song: SongState) {
    this.applySongData(song);
    const audioUrl = this.resolveAudioUrl(song.audio_url ?? null);
    if (!audioUrl) {
      this.songLabelEl.textContent = `${song.filename ?? "No song"} (missing audio URL)`;
      return;
    }
    this.waveSurferManager.load(audioUrl);
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
    this.waveSurferManager.rebuildRegions({
      sections: this.sections,
      downbeats: this.downbeats,
      showSections: this.showRegionsInput.checked,
      showDownbeats: this.showDownbeatsInput.checked,
      selectedSectionIndex: this.selectedSectionIndex,
    });
  }

  private applyZoom() {
    const nextZoom = Number(this.zoomInput.value);
    if (!Number.isFinite(nextZoom) || this.appliedZoomValue === nextZoom) return;
    this.waveSurferManager.zoom(nextZoom);
    this.appliedZoomValue = nextZoom;
  }

  private renderReadout() {
    this.positionEl.textContent = `${formatMs(this.localTimeMs)} / ${formatMs(this.durationMs)}`;
    this.barBeatEl.textContent = computeBarBeatLabel(this.downbeats, this.beats, this.localTimeMs);
  }

  private resolveAudioUrl(rawUrl: string | null): string | null {
    if (!rawUrl) return null;
    if (rawUrl.startsWith("http://") || rawUrl.startsWith("https://")) return rawUrl;
    const origin = String((globalThis as any).__BACKEND_HTTP_ORIGIN__ ?? "").trim();
    if (rawUrl.startsWith("/") && origin) return `${origin}${rawUrl}`;
    return rawUrl;
  }
}

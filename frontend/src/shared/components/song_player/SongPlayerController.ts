import { getBackendStore } from "../../state/backend_state.ts";
import { setSongPlayerTimeMs } from "../../state/song_player_time.ts";
import type { BeatObject, SongState } from "../../transport/protocol.ts";
import {
  transportPause,
  transportPlay,
  transportStop,
} from "../../transport/transport_intents.ts";
import { formatCurrentTimeMs, formatDurationMs } from "./logic/time.ts";
import type { Section } from "./types/types.ts";
import { computeBarBeatLabel } from "./logic/song_logic.ts";
import {
  implicitLoopIndex,
  loopWrapTargetMs,
  nextBeatTargetMs,
  nextSectionJump,
  previousBeatTargetMs,
  previousSectionJump,
} from "./logic/navigation_loop.ts";
import { WaveSurferManager } from "./logic/WaveSurferManager.ts";
import { PlaybackSync } from "./logic/PlaybackSync.ts";
import {
  deriveSongData,
  pausedPlaybackTimeMs,
  resolveSongAudioUrl,
  shouldAdjustWaveTime,
  songIdentity,
} from "./logic/song_player_state.ts";
import { buildWaveCallbacks } from "./logic/wave_callbacks.ts";
import { buildSongPlayerUi } from "./ui/buildSongPlayerUi.ts";

export class SongPlayerController {
  root: HTMLElement;

  private barBeatEl: HTMLElement;
  private positionEl: HTMLElement;
  private updatePlayPauseIcon: (playing: boolean) => void;
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
  private beatObjects: BeatObject[] = [];
  private beats: number[] = [];
  private downbeats: number[] = [];
  private selectedSectionIndex: number | null = null;
  private implicitLoopSectionIndex: number | null = null;
  private durationMs = 0;
  private localTimeMs = 0;
  private isPlaying = false;

  private suppressSeekSync = false;
  private appliedZoomValue: number | null = null;
  private zoomDispose: (() => void) | null = null;

  constructor() {
    const ui = buildSongPlayerUi({
      onPrevSection: () => this.jumpPrevSection(),
      onPrevBeat: () => this.jumpPrevBeat(),
      onStop: () => this.handleStop(),
      onPlayPause: () => this.togglePlayPause(),
      onNextBeat: () => this.jumpNextBeat(),
      onNextSection: () => this.jumpNextSection(),
      onLoopToggle: (checked) => {
        this.implicitLoopSectionIndex = null;
        if (checked) {
          this.primeImplicitLoopFromCurrentTime();
        }
      },
      onShowSectionsToggle: () => this.rebuildRegions(),
      onShowDownbeatsToggle: () => this.rebuildRegions(),
      onZoom: () => this.applyZoom(),
    });

    this.root = ui.root;
    this.barBeatEl = ui.barBeatEl;
    this.positionEl = ui.positionEl;
    this.updatePlayPauseIcon = ui.updatePlayPauseIcon;
    this.zoomInput = ui.zoomInput;
    this.showRegionsInput = ui.showRegionsInput;
    this.showDownbeatsInput = ui.showDownbeatsInput;
    this.songLabelEl = ui.songLabelEl;
    this.prevSectionBtn = ui.prevSectionBtn;
    this.prevBeatBtn = ui.prevBeatBtn;
    this.nextBeatBtn = ui.nextBeatBtn;
    this.nextSectionBtn = ui.nextSectionBtn;
    this.loopToggle = ui.loopToggle;
    this.zoomDispose = ui.zoomDispose;

    this.playbackSync = new PlaybackSync({
      onSync: (timeMs) => {
        this.localTimeMs = timeMs;
        this.renderReadout();
      },
    });

    this.waveSurferManager = new WaveSurferManager({
      container: ui.waveform,
      ...buildWaveCallbacks({
        setDurationMs: (durationMs) => {
          this.durationMs = durationMs;
        },
        resetAppliedZoom: () => {
          this.appliedZoomValue = null;
        },
        renderReadout: () => this.renderReadout(),
        rebuildRegions: () => this.rebuildRegions(),
        setLocalTimeMsFromSeconds: (seconds) => {
          this.localTimeMs = Math.max(0, Math.round(seconds * 1000));
        },
        enforceLoopRules: () => this.enforceLoopRules(),
        isSeekSyncSuppressed: () => this.suppressSeekSync,
        debounceSeekSync: (timeMs, isPlaying) => this.playbackSync.debounceSeekSync(timeMs, isPlaying),
        isPlaying: () => this.isPlaying,
        setIsPlaying: (playing) => {
          this.isPlaying = playing;
        },
        updatePlayPauseIcon: (playing) => this.updatePlayPauseIcon(playing),
        stopSync: () => this.playbackSync.stop(),
        syncNow: (timeMs) => this.playbackSync.syncNow(timeMs),
        getLocalTimeMs: () => this.localTimeMs,
        shouldPrimeLoopOnPlay: () => this.loopToggle.checked && this.selectedSectionIndex === null,
        primeImplicitLoopFromCurrentTime: () => this.primeImplicitLoopFromCurrentTime(),
        startSync: (getTimeMs) => this.playbackSync.start(getTimeMs),
        getWaveTimeMs: () => this.waveSurferManager.getCurrentTime() * 1000,
        setSelectedSectionIndex: (index) => {
          this.selectedSectionIndex = index;
        },
        clearImplicitLoopSectionIndex: () => {
          this.implicitLoopSectionIndex = null;
        },
      }),
    });

    this.updateControlAvailability();
  }

  refreshFromStore() {
    const state = getBackendStore().state;
    const song = state.song ?? null;
    const playback = state.playback ?? {};
    const backendPlaybackState = String(playback.state ?? "stopped");
    const backendIsPlaying = backendPlaybackState === "playing";

    if (!backendIsPlaying && this.isPlaying) {
      this.waveSurferManager.pause();
      this.isPlaying = false;
      this.playbackSync.stop();
    }

    if (song) {
      const { key: nextKey, fingerprint: nextFingerprint } = songIdentity(song);
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
      this.localTimeMs = pausedPlaybackTimeMs(playback.time_ms);
      if (this.waveSurferManager.isReady()) {
        if (shouldAdjustWaveTime(this.waveSurferManager.getCurrentTime(), this.localTimeMs)) {
          this.suppressSeekSync = true;
          this.waveSurferManager.setTime(this.localTimeMs / 1000);
          this.suppressSeekSync = false;
        }
      }
      this.renderReadout();
    }

    this.updatePlayPauseIcon(this.isPlaying);
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
      this.updatePlayPauseIcon(false);
    }
  }

  private handleStop() {
    this.playbackSync.stop();
    this.isPlaying = false;
    this.waveSurferManager.pause();
    this.waveSurferManager.setTime(0);
    this.localTimeMs = 0;
    this.renderReadout();
    this.updatePlayPauseIcon(false);
    transportStop();
    this.implicitLoopSectionIndex = null;
  }

  private jumpPrevBeat() {
    this.seekToTimeMs(previousBeatTargetMs(this.beats, this.localTimeMs));
  }

  private jumpNextBeat() {
    this.seekToTimeMs(nextBeatTargetMs(this.beats, this.localTimeMs));
  }

  private jumpPrevSection() {
    const jump = previousSectionJump(this.sections, this.localTimeMs);
    if (!jump) return;
    this.selectedSectionIndex = jump.selectedSectionIndex;
    this.implicitLoopSectionIndex = null;
    this.seekToTimeMs(jump.targetMs);
    this.rebuildRegions();
  }

  private jumpNextSection() {
    const jump = nextSectionJump(this.sections, this.localTimeMs);
    if (!jump) return;
    this.selectedSectionIndex = jump.selectedSectionIndex;
    this.implicitLoopSectionIndex = null;
    this.seekToTimeMs(jump.targetMs);
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
    this.implicitLoopSectionIndex = implicitLoopIndex(
      this.sections,
      this.loopToggle.checked,
      this.selectedSectionIndex,
      this.localTimeMs,
    );
  }

  private enforceLoopRules() {
    if (this.loopToggle.checked && this.selectedSectionIndex === null && this.implicitLoopSectionIndex === null) {
      this.primeImplicitLoopFromCurrentTime();
    }
    const wrapTargetMs = loopWrapTargetMs({
      sections: this.sections,
      loopEnabled: this.loopToggle.checked,
      selectedSectionIndex: this.selectedSectionIndex,
      implicitLoopSectionIndex: this.implicitLoopSectionIndex,
      localTimeMs: this.localTimeMs,
    });
    if (wrapTargetMs !== null) this.seekToTimeMs(wrapTargetMs);
  }

  private loadSong(song: SongState) {
    this.applySongData(song);
    const audioUrl = resolveSongAudioUrl(song.audio_url ?? null);
    if (!audioUrl) {
      this.songLabelEl.textContent = `${song.filename ?? "No song"} (missing audio URL)`;
      return;
    }
    this.waveSurferManager.load(audioUrl);
  }

  private applySongData(song: SongState) {
    const derived = deriveSongData(
      song,
      this.durationMs,
      this.selectedSectionIndex,
      this.implicitLoopSectionIndex,
    );

    this.songLabelEl.textContent = derived.label;
    this.sections = derived.sections;
    this.beatObjects = derived.beatObjects;
    this.beats = derived.beats;
    this.downbeats = derived.downbeats;
    this.durationMs = derived.durationMs;
    this.selectedSectionIndex = derived.selectedSectionIndex;
    this.implicitLoopSectionIndex = derived.implicitLoopSectionIndex;

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
    setSongPlayerTimeMs(this.localTimeMs);
    this.positionEl.textContent = `${formatCurrentTimeMs(this.localTimeMs)} / ${formatDurationMs(this.durationMs)}`;
    this.barBeatEl.textContent = computeBarBeatLabel(this.beatObjects, this.localTimeMs);
  }

  dispose() {
    this.zoomDispose?.();
    this.waveSurferManager.destroy();
    this.playbackSync.destroy();
  }
}

import type { WaveSurferManagerOptions } from "./WaveSurferManager.ts";

export type WaveCallbacksDeps = {
  setDurationMs: (durationMs: number) => void;
  resetAppliedZoom: () => void;
  applyZoom: () => void;
  renderReadout: () => void;
  rebuildRegions: () => void;
  setLocalTimeMsFromSeconds: (seconds: number) => void;
  enforceLoopRules: () => void;
  isSeekSyncSuppressed: () => boolean;
  debounceSeekSync: (timeMs: number, isPlaying: boolean) => void;
  isPlaying: () => boolean;
  setIsPlaying: (playing: boolean) => void;
  updatePlayPauseIcon: (playing: boolean) => void;
  stopSync: () => void;
  syncNow: (timeMs: number) => void;
  getLocalTimeMs: () => number;
  shouldPrimeLoopOnPlay: () => boolean;
  primeImplicitLoopFromCurrentTime: () => void;
  startSync: (getTimeMs: () => number) => void;
  getWaveTimeMs: () => number;
  setSelectedSectionIndex: (index: number | null) => void;
  clearImplicitLoopSectionIndex: () => void;
};

export function buildWaveCallbacks(
  deps: WaveCallbacksDeps,
): Omit<WaveSurferManagerOptions, "container"> {
  return {
    onReady: (durationMs) => {
      deps.setDurationMs(durationMs);
      deps.resetAppliedZoom();
      deps.applyZoom();
      deps.renderReadout();
      deps.rebuildRegions();
    },
    onTimeUpdate: (seconds) => {
      deps.setLocalTimeMsFromSeconds(seconds);
      deps.renderReadout();
      deps.enforceLoopRules();
    },
    onSeeking: (seconds) => {
      deps.setLocalTimeMsFromSeconds(seconds);
      deps.renderReadout();
      if (!deps.isSeekSyncSuppressed()) {
        deps.debounceSeekSync(deps.getLocalTimeMs(), deps.isPlaying());
      }
    },
    onFinish: () => {
      deps.setIsPlaying(false);
      deps.updatePlayPauseIcon(false);
      deps.stopSync();
      deps.syncNow(deps.getLocalTimeMs());
    },
    onPlay: () => {
      deps.setIsPlaying(true);
      deps.updatePlayPauseIcon(true);
      if (deps.shouldPrimeLoopOnPlay()) {
        deps.primeImplicitLoopFromCurrentTime();
      }
      deps.startSync(deps.getWaveTimeMs);
    },
    onPause: () => {
      if (!deps.isPlaying()) return;
      deps.setIsPlaying(false);
      deps.updatePlayPauseIcon(false);
      deps.stopSync();
      deps.syncNow(deps.getLocalTimeMs());
    },
    onSelectSection: (index) => {
      deps.setSelectedSectionIndex(index);
      deps.clearImplicitLoopSectionIndex();
      deps.rebuildRegions();
    },
  };
}

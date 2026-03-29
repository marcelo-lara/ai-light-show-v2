import { transportJumpToTime } from "../../../transport/transport_intents.ts";

const BACKEND_SYNC_INTERVAL_MS = 10_000;
const ACTIVE_PLAYBACK_SYNC_INTERVAL_MS = 50;
const RUNNING_SEEK_SYNC_DEBOUNCE_MS = 40;
const IDLE_SEEK_SYNC_DEBOUNCE_MS = 200;
const MIN_SEEK_DELTA_MS = 10;

export interface PlaybackSyncOptions {
  onSync: (localTimeMs: number) => void;
}

export class PlaybackSync {
  private rafId: number | null = null;
  private syncTimerId: number | null = null;
  private activeSyncTimerId: number | null = null;
  private seekSyncTimerId: number | null = null;
  private lastSentTimeMs: number | null = null;

  constructor(private opts: PlaybackSyncOptions) {}

  start(getCurrentTimeMs: () => number) {
    this.stop();

    // Active playback correction keeps backend output aligned to the browser audio clock.
    this.activeSyncTimerId = window.setInterval(() => {
      this.sendJumpToTime(getCurrentTimeMs(), true);
    }, ACTIVE_PLAYBACK_SYNC_INTERVAL_MS);

    // Periodic backend sync for drift alignment.
    this.syncTimerId = window.setInterval(() => {
      this.sendJumpToTime(getCurrentTimeMs(), false);
    }, BACKEND_SYNC_INTERVAL_MS);

    // Animation frame for UI updates
    const tick = () => {
      const timeMs = getCurrentTimeMs();
      this.opts.onSync(timeMs);
      this.rafId = requestAnimationFrame(tick);
    };

    this.rafId = requestAnimationFrame(tick);
  }

  stop() {
    if (this.syncTimerId !== null) {
      clearInterval(this.syncTimerId);
      this.syncTimerId = null;
    }
    if (this.activeSyncTimerId !== null) {
      clearInterval(this.activeSyncTimerId);
      this.activeSyncTimerId = null;
    }
    if (this.rafId !== null) {
      cancelAnimationFrame(this.rafId);
      this.rafId = null;
    }
    if (this.seekSyncTimerId !== null) {
      clearTimeout(this.seekSyncTimerId);
      this.seekSyncTimerId = null;
    }
  }

  debounceSeekSync(timeMs: number, isPlaying: boolean) {
    if (this.seekSyncTimerId !== null) {
      clearTimeout(this.seekSyncTimerId);
    }
    const delayMs = isPlaying ? RUNNING_SEEK_SYNC_DEBOUNCE_MS : IDLE_SEEK_SYNC_DEBOUNCE_MS;
    this.seekSyncTimerId = window.setTimeout(() => {
      this.seekSyncTimerId = null;
      this.sendJumpToTime(timeMs, false);
    }, delayMs);
  }

  syncNow(timeMs: number) {
    if (this.seekSyncTimerId !== null) {
      clearTimeout(this.seekSyncTimerId);
      this.seekSyncTimerId = null;
    }
    this.sendJumpToTime(timeMs, false);
  }

  destroy() {
    this.stop();
    if (this.seekSyncTimerId !== null) {
      clearTimeout(this.seekSyncTimerId);
    }
  }

  private sendJumpToTime(timeMs: number, sync: boolean) {
    const nextTimeMs = Math.max(0, Math.round(timeMs));
    if (
      this.lastSentTimeMs !== null &&
      Math.abs(this.lastSentTimeMs - nextTimeMs) < MIN_SEEK_DELTA_MS
    ) {
      return;
    }
    this.lastSentTimeMs = nextTimeMs;
    transportJumpToTime(nextTimeMs, { sync });
  }
}

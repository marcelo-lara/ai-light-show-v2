import { transportJumpToTime } from "../../../transport/transport_intents.ts";

const BACKEND_SYNC_INTERVAL_MS = 10_000;

export interface PlaybackSyncOptions {
  onSync: (localTimeMs: number) => void;
}

export class PlaybackSync {
  private rafId: number | null = null;
  private syncTimerId: number | null = null;
  private seekSyncTimerId: number | null = null;

  constructor(private opts: PlaybackSyncOptions) {}

  start(getCurrentTimeMs: () => number) {
    this.stop();

    // Periodic backend sync for drift alignment.
    this.syncTimerId = window.setInterval(() => {
      transportJumpToTime(getCurrentTimeMs());
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
    if (this.rafId !== null) {
      cancelAnimationFrame(this.rafId);
      this.rafId = null;
    }
    if (this.seekSyncTimerId !== null) {
      clearTimeout(this.seekSyncTimerId);
      this.seekSyncTimerId = null;
    }
  }

  debounceSeekSync(timeMs: number) {
    if (this.seekSyncTimerId !== null) {
      clearTimeout(this.seekSyncTimerId);
    }
    this.seekSyncTimerId = window.setTimeout(() => {
      this.seekSyncTimerId = null;
      transportJumpToTime(timeMs);
    }, 120);
  }

  syncNow(timeMs: number) {
    transportJumpToTime(timeMs);
  }

  destroy() {
    this.stop();
    if (this.seekSyncTimerId !== null) {
      clearTimeout(this.seekSyncTimerId);
    }
  }
}

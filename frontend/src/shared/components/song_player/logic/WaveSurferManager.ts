import WaveSurfer from "wavesurfer.js";
import RegionsPlugin from "wavesurfer.js/dist/plugins/regions.esm.js";
import type { Section } from "../types/types.ts";
import { rebuildSongRegions } from "./regions.ts";

export interface WaveSurferManagerOptions {
  container: HTMLElement;
  onReady: (durationMs: number) => void;
  onTimeUpdate: (seconds: number) => void;
  onSeeking: (seconds: number) => void;
  onFinish: () => void;
  onPlay: () => void;
  onPause: () => void;
  onSelectSection: (index: number | null) => void;
}

export class WaveSurferManager {
  private waveSurfer: any | null = null;
  private regionsPlugin: any | null = null;
  private hasAudioLoaded = false;

  constructor(private opts: WaveSurferManagerOptions) {
    this.init();
  }

  private init() {
    this.waveSurfer = WaveSurfer.create({
      container: this.opts.container,
      waveColor: "#999",//"var(--accent)",
      progressColor: "#ddd",
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
      const durationMs = Math.max(0, Math.round(Number(durationSec || 0) * 1000));
      this.opts.onReady(durationMs);
    });

    this.waveSurfer.on("timeupdate", (seconds: number) => {
      this.opts.onTimeUpdate(seconds);
    });

    this.waveSurfer.on("seeking", (seconds: number) => {
      this.opts.onSeeking(seconds);
    });

    this.waveSurfer.on("finish", () => this.opts.onFinish());
    this.waveSurfer.on("play", () => this.opts.onPlay());
    this.waveSurfer.on("pause", () => this.opts.onPause());

    this.waveSurfer.on("error", () => {
      this.hasAudioLoaded = false;
    });
  }

  load(url: string) {
    this.hasAudioLoaded = false;
    this.waveSurfer.load(url);
  }

  play() {
    return this.waveSurfer?.play();
  }

  pause() {
    this.waveSurfer?.pause();
  }

  setTime(seconds: number) {
    if (this.hasAudioLoaded) {
      try {
        this.waveSurfer.setTime(seconds);
      } catch (e) {}
    }
  }

  getCurrentTime(): number {
    if (!this.waveSurfer || !this.hasAudioLoaded) return 0;
    try {
      return Number(this.waveSurfer.getCurrentTime() ?? 0);
    } catch {
      return 0;
    }
  }

  zoom(value: number) {
    if (this.hasAudioLoaded) {
      try {
        this.waveSurfer.zoom(value);
      } catch (e) {}
    }
  }

  rebuildRegions(params: {
    sections: Section[];
    downbeats: number[];
    showSections: boolean;
    showDownbeats: boolean;
    selectedSectionIndex: number | null;
  }) {
    rebuildSongRegions({
      regionsPlugin: this.regionsPlugin,
      sections: params.sections,
      downbeats: params.downbeats,
      showSections: params.showSections,
      showDownbeats: params.showDownbeats,
      selectedSectionIndex: params.selectedSectionIndex,
      onSelectSection: this.opts.onSelectSection,
    });
  }

  isReady() {
    return this.hasAudioLoaded;
  }

  destroy() {
    this.waveSurfer?.destroy();
  }
}

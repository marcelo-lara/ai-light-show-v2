import { SongPlayerController } from "./SongPlayerController.ts";

let singleton: SongPlayerController | null = null;

export function SongPlayer(): HTMLElement {
  if (!singleton) {
    singleton = new SongPlayerController();
  }
  singleton.refreshFromStore();
  return singleton.root;
}

export function refreshSongPlayer() {
  singleton?.refreshFromStore();
}

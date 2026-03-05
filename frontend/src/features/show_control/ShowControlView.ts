import { SongPlayer } from "../../shared/components/song_player/SongPlayer.ts";

export function ShowControlView(): HTMLElement {
  const view = document.createElement("section");
  view.className = "view";

  const description = document.createElement("p");
  description.textContent = "Show Control is available as a navigation target. Feature implementation is pending.";

  view.append(SongPlayer(), description);
  return view;
}

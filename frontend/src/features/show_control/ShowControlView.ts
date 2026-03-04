import { SongPlayer } from "../../shared/components/song_player/SongPlayer.ts";

export function ShowControlView(): HTMLElement {
  const view = document.createElement("section");
  view.className = "view";

  const title = document.createElement("h1");
  title.textContent = "Show Control";

  const description = document.createElement("p");
  description.textContent = "Show Control is available as a navigation target. Feature implementation is pending.";

  view.append(title, SongPlayer(), description);
  return view;
}

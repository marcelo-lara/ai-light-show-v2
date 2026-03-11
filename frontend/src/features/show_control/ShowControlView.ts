import { SongPlayer } from "../../shared/components/song_player/SongPlayer.ts";
import { SongPartsPanel } from "./components/SongPartsPanel.ts";
import { CueSheetPanel } from "./components/CueSheetPanel.ts";
import { FixtureEffectsPanel } from "./components/FixtureEffectsPanel.ts";

export function ShowControlView(): HTMLElement {
  const view = document.createElement("section");
  view.className = "view";

  const main = document.createElement("div");
  main.className = "show-control-main";
  main.append(SongPartsPanel(), CueSheetPanel(), FixtureEffectsPanel());

  view.append(SongPlayer(), main);
  return view;
}

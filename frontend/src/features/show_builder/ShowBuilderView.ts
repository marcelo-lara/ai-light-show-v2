import { SongProgression } from "./components/SongProgression.ts";
import { EffectPlaylist } from "./components/EffectPlaylist.ts";
import { EffectPicker } from "./components/EffectPicker.ts";
import { SongPlayer } from "../../shared/components/song_player/SongPlayer.ts";

export function ShowBuilderView(): HTMLElement {
	const wrap = document.createElement("section");
	wrap.className = "view";

	const main = document.createElement("div");
	main.className = "show-builder-main";
	main.append(SongProgression(), EffectPlaylist(), EffectPicker());

	wrap.append(SongPlayer(), main);
	return wrap;
}

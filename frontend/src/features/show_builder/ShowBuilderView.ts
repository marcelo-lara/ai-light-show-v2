import { SongProgression } from "./components/SongProgression.ts";
import { EffectPlaylist } from "./components/EffectPlaylist.ts";
import { EffectPicker } from "./components/EffectPicker.ts";

export function ShowBuilderView(): HTMLElement {
	const wrap = document.createElement("section");
	wrap.className = "view";
	const title = document.createElement("h1");
	title.textContent = "Show Builder";
	wrap.append(title, SongProgression(), EffectPlaylist(), EffectPicker());
	return wrap;
}

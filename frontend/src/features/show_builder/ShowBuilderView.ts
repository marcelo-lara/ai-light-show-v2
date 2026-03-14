import { EffectPlaylist } from "./components/effect_playlist/EffectPlaylist.ts";
import { EffectPicker } from "./components/effect_picker/EffectPicker.ts";
import { SongPlayer } from "../../shared/components/song_player/SongPlayer.ts";
import { ChordsPanel } from "../../shared/components/chords_panel/ChordsPanel.ts";
import { getSongStructureData } from "../../shared/state/song_data.ts";

export function ShowBuilderView(): HTMLElement {
	const wrap = document.createElement("section");
	wrap.className = "view";
	const song = getSongStructureData();

	const main = document.createElement("div");
	main.className = "show-builder-main";
	main.append(
		ChordsPanel({ beats: song.beats, sections: song.sections, cardClassName: "show-builder-panel" }),
		EffectPlaylist(),
		EffectPicker(),
	);

	wrap.append(SongPlayer(), main);
	return wrap;
}

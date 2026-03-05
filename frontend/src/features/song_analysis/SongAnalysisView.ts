import { AnalysisPlot } from "./components/AnalysisPlot.ts";
import { BeatTable } from "./components/BeatTable.ts";
import { ChordsPanel } from "./components/ChordsPanel.ts";
import { SongPlayer } from "../../shared/components/song_player/SongPlayer.ts";

export function SongAnalysisView(): HTMLElement {
	const wrap = document.createElement("section");
	wrap.className = "view";
	wrap.append(SongPlayer(), AnalysisPlot(), BeatTable(), ChordsPanel());
	return wrap;
}

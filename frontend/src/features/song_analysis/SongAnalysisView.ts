import { AnalysisPlot } from "./components/AnalysisPlot.ts";
import { SongPlayer } from "../../shared/components/song_player/SongPlayer.ts";
import { Columns } from "../../shared/components/layout/Columns.ts";
import { Cards } from "../../shared/components/layout/Cards.ts";
import { ChordsPanel } from "../../shared/components/chords_panel/ChordsPanel.ts";
import { getSongAnalysisData } from "./song_analysis_state.ts";

export function SongAnalysisView(): HTMLElement {
	const wrap = document.createElement("section");
	wrap.className = "view song-analysis-view";
	const data = getSongAnalysisData();

	const left = Cards([
		ChordsPanel({ chords: data.chords, sections: data.sections }),
	], { className: "song-analysis-left" });
	const right = AnalysisPlot({ plots: data.plots });

	wrap.append(SongPlayer(), Columns(left, right, { leftColPx: 300, className: "song-analysis-columns" }));
	return wrap;
}

import { AnalysisPlot } from "./components/AnalysisPlot.ts";
import { BeatTable } from "./components/BeatTable.ts";
import { ChordsPanel } from "./components/ChordsPanel.ts";
import { SongPlayer } from "../../shared/components/song_player/SongPlayer.ts";
import { Columns } from "../../shared/components/layout/Columns.ts";
import { Cards } from "../../shared/components/layout/Cards.ts";
import { getSongAnalysisData } from "./song_analysis_state.ts";

export function SongAnalysisView(): HTMLElement {
	const wrap = document.createElement("section");
	wrap.className = "view";
	const data = getSongAnalysisData();

	const left = Cards([
		BeatTable({ beats: data.beats, downbeats: data.downbeats }),
		ChordsPanel({ chords: data.chords }),
	]);
	const right = AnalysisPlot({ plots: data.plots });

	wrap.append(SongPlayer(), Columns(left, right));
	return wrap;
}

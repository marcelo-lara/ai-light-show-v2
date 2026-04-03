import { AnalysisPlot } from "./components/AnalysisPlot.ts";
import { SongPlayer } from "../../shared/components/song_player/SongPlayer.ts";
import { Columns } from "../../shared/components/layout/Columns.ts";
import { Cards } from "../../shared/components/layout/Cards.ts";
import { SongLoaderPanel } from "./song_loader/SongLoaderPanel.ts";
import { AnalyzerQueuePanel } from "./analyzer_queue/AnalyzerQueuePanel.ts";
import { getSongAnalysisData } from "./song_analysis_state.ts";

export function SongAnalysisView(): HTMLElement {
	const wrap = document.createElement("section");
	wrap.className = "view song-analysis-view";
	const data = getSongAnalysisData();
	const songLoader = SongLoaderPanel();
	const analyzerQueue = AnalyzerQueuePanel();

	const left = Cards([
		songLoader,
		analyzerQueue,
	], { className: "song-analysis-left" });
	const right = AnalysisPlot({ plots: data.plots });

	wrap.append(SongPlayer(), Columns(left, right, { leftColPx: 300, className: "song-analysis-columns" }));
	(wrap as unknown as { _cleanup?: () => void })._cleanup = () => {
		(songLoader as unknown as { _cleanup?: () => void })._cleanup?.();
		(analyzerQueue as unknown as { _cleanup?: () => void })._cleanup?.();
	};
	return wrap;
}

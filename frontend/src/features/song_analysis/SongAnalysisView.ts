import { AnalysisPlot } from "./components/AnalysisPlot.ts";
import { BeatTable } from "./components/BeatTable.ts";
import { ChordsPanel } from "./components/ChordsPanel.ts";

export function SongAnalysisView(): HTMLElement {
	const wrap = document.createElement("section");
	wrap.className = "view";
	const title = document.createElement("h1");
	title.textContent = "Song Analysis";
	wrap.append(title, AnalysisPlot(), BeatTable(), ChordsPanel());
	return wrap;
}

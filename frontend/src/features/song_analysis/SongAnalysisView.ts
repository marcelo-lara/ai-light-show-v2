import { AnalysisPlot } from "./components/AnalysisPlot.ts";
import { SongPlayer } from "../../shared/components/song_player/SongPlayer.ts";
import { Cards } from "../../shared/components/layout/Cards.ts";
import { Card } from "../../shared/components/layout/Card.ts";
import { ChordsPanel } from "../../shared/components/chords_panel/ChordsPanel.ts";
import { SongLoaderPanel } from "./song_loader/SongLoaderPanel.ts";
import { ChordPatternsPanel } from "./chord_patterns/ChordPatternsPanel.ts";
import { getSongAnalysisData } from "./song_analysis_state.ts";
import { SongEventsPanel } from "./song_events/SongEventsPanel.ts";


function EventToolsPlaceholder(): HTMLElement {
	const content = document.createElement("div");
	content.className = "song-analysis-placeholder";

	const title = document.createElement("p");
	title.className = "song-analysis-placeholder-title";
	title.textContent = "Event Tools";

	const body = document.createElement("p");
	body.className = "muted song-analysis-placeholder-copy";
	body.textContent = "Filters and event actions land here.";

	content.append(title, body);
	return Card(content, { variant: "outlined", className: "song-analysis-placeholder-card" });
}

export function SongAnalysisView(): HTMLElement {
	const wrap = document.createElement("section");
	wrap.className = "view song-analysis-view";
	const data = getSongAnalysisData();
	const songLoader = SongLoaderPanel();
	const chords = ChordsPanel({ beats: data.beats, sections: data.sections, cardClassName: "song-analysis-chords-card" });
	const events = SongEventsPanel(data.events);
	const patterns = ChordPatternsPanel(data.patterns);
	const eventTools = EventToolsPlaceholder();
	const plots = AnalysisPlot({ plots: data.plots });

	const firstColumn = Cards([
		songLoader,
		chords,
	], { className: "song-analysis-column song-analysis-column-primary" });
	const secondColumn = Cards([
		events,
		eventTools,
	], { className: "song-analysis-column song-analysis-column-events" });

	const thirdColumn = document.createElement("div");
	thirdColumn.className = "song-analysis-column song-analysis-column-patterns";
	thirdColumn.append(patterns);

	const fourthColumn = document.createElement("div");
	fourthColumn.className = "song-analysis-column song-analysis-column-plots";
	fourthColumn.append(plots);

	const grid = document.createElement("div");
	grid.className = "song-analysis-columns";
	grid.append(firstColumn, secondColumn, thirdColumn, fourthColumn);

	wrap.append(SongPlayer(), grid);
	(wrap as unknown as { _cleanup?: () => void })._cleanup = () => {
		(songLoader as unknown as { _cleanup?: () => void })._cleanup?.();
		(events as unknown as { _cleanup?: () => void })._cleanup?.();
		(patterns as unknown as { _cleanup?: () => void })._cleanup?.();
	};
	return wrap;
}

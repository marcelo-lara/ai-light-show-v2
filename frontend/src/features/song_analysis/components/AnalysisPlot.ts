import { Card } from "../../../shared/components/layout/Card.ts";

type Plot = {
  id: string;
  title: string;
  svgUrl: string;
};

type AnalysisPlotProps = {
  plots: Plot[];
};

export function AnalysisPlot(props: AnalysisPlotProps): HTMLElement {
	const content = document.createElement("div");
	content.className = "analysis-card analysis-plots";

	if (!props.plots.length) {
		const empty = document.createElement("p");
		empty.className = "muted";
		empty.textContent = "No analysis plots available for current song.";
		content.appendChild(empty);
		return Card(content, { variant: "outlined" });
	}

	for (const plot of props.plots) {
		const row = document.createElement("section");
		row.className = "analysis-plot-row";

		const label = document.createElement("p");
		label.className = "analysis-plot-label";
		label.textContent = plot.title;

		const img = document.createElement("img");
		img.className = "analysis-plot-img";
		img.alt = plot.title;
		img.loading = "lazy";
		img.addEventListener("error", () => row.remove(), { once: true });
		img.src = plot.svgUrl;

		row.append(label, img);
		content.appendChild(row);
	}

	return Card(content, { variant: "outlined", className: "analysis-plots-card" });
}

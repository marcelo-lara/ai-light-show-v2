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
	content.className = "analysis-card";

	const title = document.createElement("h3");
	title.textContent = "Analysis Plot";
	content.appendChild(title);

	if (!props.plots.length) {
		const empty = document.createElement("p");
		empty.textContent = "No analysis plots available for current song.";
		content.appendChild(empty);
		return Card(content, { variant: "outlined" });
	}

	const picker = document.createElement("select");
	picker.className = "analysis-plot-select";
	for (const plot of props.plots) {
		const option = document.createElement("option");
		option.value = plot.id;
		option.textContent = plot.title;
		picker.appendChild(option);
	}
	content.appendChild(picker);

	const img = document.createElement("img");
	img.className = "analysis-plot-img";
	img.alt = "Song analysis plot";
	img.loading = "lazy";

	const setPlot = (id: string) => {
		const selected = props.plots.find((plot) => plot.id === id) ?? props.plots[0];
		img.src = selected.svgUrl;
		img.alt = selected.title;
	};

	picker.addEventListener("change", () => setPlot(picker.value));
	setPlot(props.plots[0].id);
	content.appendChild(img);

	return Card(content, { variant: "outlined" });
}

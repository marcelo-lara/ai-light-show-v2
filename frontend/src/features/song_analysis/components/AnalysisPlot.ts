export function AnalysisPlot(): HTMLElement {
	const panel = document.createElement("section");
	panel.className = "subpanel";
	panel.innerHTML = "<h3>Analysis Plot</h3><p>Awaiting backend analysis data.</p>";
	return panel;
}

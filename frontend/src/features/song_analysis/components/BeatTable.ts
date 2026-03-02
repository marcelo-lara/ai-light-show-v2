export function BeatTable(): HTMLElement {
	const panel = document.createElement("section");
	panel.className = "subpanel";
	panel.innerHTML = "<h3>Beat Table</h3><p>No beat rows yet.</p>";
	return panel;
}

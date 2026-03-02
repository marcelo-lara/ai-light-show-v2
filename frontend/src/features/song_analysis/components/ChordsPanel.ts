export function ChordsPanel(): HTMLElement {
	const panel = document.createElement("section");
	panel.className = "subpanel";
	panel.innerHTML = "<h3>Chords</h3><p>No chord data yet.</p>";
	return panel;
}

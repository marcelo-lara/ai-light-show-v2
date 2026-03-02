export function EffectPicker(): HTMLElement {
	const panel = document.createElement("section");
	panel.className = "subpanel";
	panel.innerHTML = "<h3>Effect Picker</h3><p>Choose fixture effects here.</p>";
	return panel;
}

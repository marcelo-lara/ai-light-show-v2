export function EffectPlaylist(): HTMLElement {
	const panel = document.createElement("section");
	panel.className = "subpanel";
	panel.innerHTML = "<h3>Effect Playlist</h3><p>No effects queued.</p>";
	return panel;
}

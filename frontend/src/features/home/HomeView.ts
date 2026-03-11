export function HomeView(): HTMLElement {
	const wrap = document.createElement("section");
	wrap.className = "view";

	const text = document.createElement("p");
	text.textContent = "Backend-authoritative light show console. Select a route to begin.";

	wrap.append(text);
	return wrap;
}

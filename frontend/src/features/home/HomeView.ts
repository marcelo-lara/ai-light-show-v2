export function HomeView(): HTMLElement {
	const wrap = document.createElement("section");
	wrap.className = "view";

	const title = document.createElement("h1");
	title.textContent = "Home";
	const text = document.createElement("p");
	text.textContent = "Backend-authoritative light show console. Select a route to begin.";

	wrap.append(title, text);
	return wrap;
}

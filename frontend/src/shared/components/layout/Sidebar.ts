import { ROUTES } from "../../../app/routes.ts";
import { getUiState, setRoute, type Route } from "../../state/ui_state.ts";

export function Sidebar(): HTMLElement {
	const sidebar = document.createElement("aside");
	sidebar.className = "sidebar";

	const title = document.createElement("div");
	title.className = "sidebar-title";
	title.textContent = "AI Light Show";

	const nav = document.createElement("nav");
	nav.className = "sidebar-nav";

	const active = getUiState().route;
	for (const route of ROUTES) {
		nav.appendChild(createRouteButton(route.id, route.label, active === route.id));
	}

	sidebar.append(title, nav);
	return sidebar;
}

function createRouteButton(route: Route, label: string, isActive: boolean): HTMLButtonElement {
	const button = document.createElement("button");
	button.type = "button";
	button.className = `nav-btn ${isActive ? "active" : ""}`.trim();
	button.textContent = label;
	button.addEventListener("click", () => setRoute(route));
	return button;
}

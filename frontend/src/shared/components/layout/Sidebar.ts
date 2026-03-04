import { ROUTES, type RouteIcon } from "../../../app/routes.ts";
import { getUiState, setRoute, type Route } from "../../state/ui_state.ts";

export function Sidebar(): HTMLElement {
	const sidebar = document.createElement("aside");
	sidebar.className = "sidebar";

	const nav = document.createElement("nav");
	nav.className = "sidebar-nav";

	const active = getUiState().route;
	for (const route of ROUTES) {
		nav.appendChild(createRouteButton(route.id, route.label, route.icon, active === route.id));
	}

	sidebar.append(nav);
	return sidebar;
}

function createRouteButton(route: Route, label: string, icon: RouteIcon, isActive: boolean): HTMLButtonElement {
	const button = document.createElement("button");
	button.type = "button";
	button.className = `nav-btn ${isActive ? "active" : ""}`.trim();
	button.setAttribute("aria-label", label);
	button.title = label;
	button.appendChild(createIcon(icon));
	button.addEventListener("click", () => setRoute(route));
	return button;
}

function createIcon(icon: RouteIcon): SVGElement {
	const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
	svg.setAttribute("viewBox", "0 0 24 24");
	svg.setAttribute("fill", "none");
	svg.setAttribute("stroke", "currentColor");
	svg.setAttribute("stroke-width", "2");
	svg.setAttribute("stroke-linecap", "round");
	svg.setAttribute("stroke-linejoin", "round");
	svg.classList.add("nav-icon");

	const paths = iconPaths(icon);
	for (const d of paths) {
		const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
		path.setAttribute("d", d);
		svg.appendChild(path);
	}

	return svg;
}

function iconPaths(icon: RouteIcon): string[] {
	if (icon === "wave") {
		return ["M3 12c2 0 2-4 4-4s2 8 4 8 2-8 4-8 2 4 4 4 2-2 2-2"];
	}
	if (icon === "build") {
		return ["M12 3v18", "M3 12h18", "M6 6l12 12", "M18 6L6 18"];
	}
	if (icon === "dmx") {
		return ["M4 7h16", "M4 12h16", "M4 17h16", "M7 4v16", "M12 4v16", "M17 4v16"];
	}
	return ["M12 3v6", "M12 15v6", "M3 12h6", "M15 12h6", "M6 6l4 4", "M14 14l4 4", "M18 6l-4 4", "M10 14l-4 4"];
}

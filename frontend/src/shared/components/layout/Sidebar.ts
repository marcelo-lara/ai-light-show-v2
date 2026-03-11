import { ROUTES, type RouteIcon } from "../../../app/routes.ts";
import { getUiState, setRoute, type Route } from "../../state/ui_state.ts";
import { createSvgIcon } from "../../utils/svg.ts";
import { ICON_REGISTRY } from "../../svg_icons/index.ts";

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
	
	const paths = ICON_REGISTRY[icon];
	button.appendChild(createSvgIcon(paths, "nav-icon"));

	button.addEventListener("click", () => setRoute(route));
	return button;
}


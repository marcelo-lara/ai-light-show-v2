import type { IconPath } from "../svg_icons/index.ts";

export function createSvgIcon(paths: IconPath[], className?: string): SVGElement {
	const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
	svg.setAttribute("viewBox", "0 0 24 24");
	svg.setAttribute("fill", "none");
	svg.setAttribute("stroke", "currentColor");
	svg.setAttribute("stroke-width", "2");
	svg.setAttribute("stroke-linecap", "round");
	svg.setAttribute("stroke-linejoin", "round");
	if (className) {
		svg.classList.add(className);
	}

	for (const p of paths) {
		const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
		path.setAttribute("d", p.d);
		if (p.isAccent) {
			path.classList.add("svg-accent");
		}
		svg.appendChild(path);
	}

	return svg;
}

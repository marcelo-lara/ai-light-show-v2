export function Badge(label: string, tone: "default" | "ok" | "warn" | "err" = "default"): HTMLElement {
	const node = document.createElement("span");
	node.className = `badge ${tone}`;
	node.textContent = label;
	return node;
}

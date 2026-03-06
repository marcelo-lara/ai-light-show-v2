export function Badge(label: string, tone: "default" | "ok" | "warn" | "err" = "default", testId?: string): HTMLElement {
	const node = document.createElement("span");
	node.className = `badge ${tone}`;
	if (testId) node.setAttribute("data-testid", testId);
	node.textContent = label;
	return node;
}

type RowTag = "article" | "div" | "li";

type ListOptions = {
	tagName?: RowTag;
	className?: string;
	contentClassName?: string;
	actionsClassName?: string;
	content: Node | Node[];
	actions?: Node | Node[];
	onSelect?: () => void;
	isActive?: boolean;
	title?: string;
	dataset?: Record<string, string>;
};

function appendNodes(parent: HTMLElement, nodes: Node | Node[] | undefined): void {
	if (!nodes) return;
	if (Array.isArray(nodes)) {
		parent.append(...nodes);
		return;
	}
	parent.append(nodes);
}

export function List(options: ListOptions): HTMLElement {
	const row = document.createElement(options.tagName ?? "article");
	row.className = `o-list-row ${options.className ?? ""}`.trim();
	row.classList.toggle("is-active", Boolean(options.isActive));

	if (options.title) {
		row.title = options.title;
	}
	for (const [name, value] of Object.entries(options.dataset ?? {})) {
		row.dataset[name] = value;
	}

	const content = document.createElement("div");
	content.className = `o-list-content ${options.contentClassName ?? ""}`.trim();
	appendNodes(content, options.content);
	if (options.onSelect) {
		content.addEventListener("click", options.onSelect);
	}

	const actions = document.createElement("div");
	actions.className = `o-list-actions ${options.actionsClassName ?? ""}`.trim();
	appendNodes(actions, options.actions);

	row.append(content, actions);
	return row;
}

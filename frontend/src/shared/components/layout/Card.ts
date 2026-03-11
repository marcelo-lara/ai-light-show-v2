export type CardOptions = {
	title?: string;
	className?: string;
	variant?: "plain" | "outlined";
};

export function Card(content: HTMLElement, options: CardOptions = {}): HTMLElement {
	const card = document.createElement("section");
	const variantClass = options.variant === "outlined" ? "card--outlined" : "";
	card.className = `card ${variantClass} ${options.className ?? ""}`.trim();

	if (options.title) {
		const header = document.createElement("header");
		header.className = "card-header";
		header.textContent = options.title;
		card.appendChild(header);
	}

	card.appendChild(content);
	return card;
}

export type CardOptions = {
	title?: string;
	className?: string;
	variant?: "plain" | "outlined";
	ariaLabel?: string;
};

export function Card(content: HTMLElement, options: CardOptions = {}): HTMLElement {
	const card = document.createElement("section");
	const variantClass = options.variant === "outlined" ? "card-outlined" : "";
	card.className = `card ${variantClass} ${options.className ?? ""}`.trim();
	if (options.ariaLabel) {
		card.setAttribute("aria-label", options.ariaLabel);
	}

	if (options.title) {
		const header = document.createElement("header");
		header.className = "card-header";
		header.textContent = options.title;
		card.appendChild(header);
	}

	card.appendChild(content);
	return card;
}

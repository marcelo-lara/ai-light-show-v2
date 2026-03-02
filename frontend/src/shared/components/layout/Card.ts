export type CardOptions = {
	title?: string;
	className?: string;
};

export function Card(content: HTMLElement, options: CardOptions = {}): HTMLElement {
	const card = document.createElement("section");
	card.className = `card ${options.className ?? ""}`.trim();

	if (options.title) {
		const header = document.createElement("header");
		header.className = "card-header";
		header.textContent = options.title;
		card.appendChild(header);
	}

	card.appendChild(content);
	return card;
}

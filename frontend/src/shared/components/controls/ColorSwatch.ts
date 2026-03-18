export type ColorSwatchProps = {
	color: string;
	label?: string;
	onSelect?: (color: string) => void;
};

export function ColorSwatch(props: ColorSwatchProps): HTMLElement {
	const button = document.createElement("button");
	button.type = "button";
	button.textContent = props.label ?? props.color;
	button.title = props.label ?? props.color;
	button.addEventListener("click", () => props.onSelect?.(props.color));
	return button;
}

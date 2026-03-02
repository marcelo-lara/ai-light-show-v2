export type ToggleProps = {
	label: string;
	checked: boolean;
	onChange?: (checked: boolean) => void;
};

export function Toggle(props: ToggleProps): HTMLElement {
	const label = document.createElement("label");
	label.className = "toggle";

	const text = document.createElement("span");
	text.textContent = props.label;

	const input = document.createElement("input");
	input.type = "checkbox";
	input.checked = props.checked;
	input.addEventListener("change", () => props.onChange?.(input.checked));

	label.append(text, input);
	return label;
}

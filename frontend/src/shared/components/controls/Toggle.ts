export type ToggleProps = {
	label: string;
	checked: boolean;
	className?: string;
	onChange?: (checked: boolean) => void;
};

export type ToggleControl = {
	root: HTMLLabelElement;
	input: HTMLInputElement;
	setChecked: (checked: boolean) => void;
};

export function Toggle(props: ToggleProps): ToggleControl {
	const label = document.createElement("label");
	label.className = `toggle${props.className ? ` ${props.className}` : ""}`;

	const text = document.createElement("span");
	text.textContent = props.label;

	const input = document.createElement("input");
	input.type = "checkbox";
	input.checked = props.checked;
	input.addEventListener("change", () => props.onChange?.(input.checked));

	label.append(text, input);
	return {
		root: label,
		input,
		setChecked: (checked) => {
			input.checked = checked;
		},
	};
}

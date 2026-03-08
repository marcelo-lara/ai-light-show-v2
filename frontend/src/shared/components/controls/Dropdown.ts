export type DropdownOption = { value: string; label: string };

export type DropdownProps = {
	label?: string;
	value: string;
	options: DropdownOption[];
	onChange?: (value: string) => void;
};

export function Dropdown(props: DropdownProps): HTMLElement {
	const wrap = document.createElement("label");
	wrap.className = "dropdown";

	if (props.label) {
		const text = document.createElement("span");
		text.textContent = props.label;
		wrap.appendChild(text);
	}

	const select = document.createElement("select");
	for (const option of props.options) {
		const node = document.createElement("option");
		node.value = option.value;
		node.textContent = option.label;
		node.selected = option.value === props.value;
		select.appendChild(node);
	}
	select.addEventListener("change", () => props.onChange?.(select.value));

	wrap.append(select);
	return wrap;
}

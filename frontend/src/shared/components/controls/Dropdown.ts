export type DropdownOption = { value: string; label: string };

export type DropdownProps = {
	label?: string;
	value: string;
	options: DropdownOption[];
	attributes?: Record<string, string>;
	onChange?: (value: string) => void;
};

export type DropdownControl = {
	root: HTMLLabelElement;
	select: HTMLSelectElement;
	setOptions: (options: DropdownOption[], value?: string) => void;
	setValue: (value: string) => void;
};

function applyOptions(select: HTMLSelectElement, options: DropdownOption[], value: string): void {
	select.innerHTML = "";
	for (const option of options) {
		const node = document.createElement("option");
		node.value = option.value;
		node.textContent = option.label;
		node.selected = option.value === value;
		select.appendChild(node);
	}
	select.value = value;
}

export function Dropdown(props: DropdownProps): DropdownControl {
	const wrap = document.createElement("label");
	wrap.className = "dropdown";

	if (props.label) {
		const text = document.createElement("span");
		text.textContent = props.label;
		wrap.appendChild(text);
	}

	const select = document.createElement("select");
	for (const [name, value] of Object.entries(props.attributes ?? {})) {
		select.setAttribute(name, value);
	}
	applyOptions(select, props.options, props.value);
	select.addEventListener("change", () => props.onChange?.(select.value));

	wrap.append(select);
	return {
		root: wrap,
		select,
		setOptions: (options, value) => {
			applyOptions(select, options, value ?? select.value);
		},
		setValue: (value) => {
			select.value = value;
		},
	};
}

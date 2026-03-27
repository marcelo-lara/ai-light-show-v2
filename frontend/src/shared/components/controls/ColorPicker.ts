export type ColorPickerProps = {
	label?: string;
	value: string;
	disabled?: boolean;
	onChange?: (value: string) => void;
};

export type ColorPickerControl = {
	root: HTMLLabelElement;
	input: HTMLInputElement;
	setValue: (value: string) => void;
	dispose: () => void;
};

function normalizeColor(value: string): string {
	const clean = String(value || "").trim().replace(/^#/, "");
	return /^[0-9a-fA-F]{6}$/.test(clean) ? `#${clean.toUpperCase()}` : "#FFFFFF";
}

export function ColorPicker(props: ColorPickerProps): ColorPickerControl {
	const root = document.createElement("label");
	root.className = "color-picker";

	if (props.label) {
		const caption = document.createElement("span");
		caption.textContent = props.label;
		root.appendChild(caption);
	}

	const shell = document.createElement("span");
	shell.className = "color-picker-shell";

	const input = document.createElement("input");
	input.className = "color-picker-input";
	input.type = "color";
	input.value = normalizeColor(props.value);
	input.disabled = Boolean(props.disabled);

	const value = document.createElement("span");
	value.className = "color-picker-value mono muted";
	value.textContent = input.value;

	const emit = () => {
		const next = normalizeColor(input.value);
		input.value = next;
		value.textContent = next;
		props.onChange?.(next);
	};

	input.addEventListener("input", emit);
	input.addEventListener("change", emit);
	shell.append(input, value);
	root.appendChild(shell);

	return {
		root,
		input,
		setValue: (next) => {
			const normalized = normalizeColor(next);
			input.value = normalized;
			value.textContent = normalized;
		},
		dispose: () => {
			input.removeEventListener("input", emit);
			input.removeEventListener("change", emit);
		},
	};
}
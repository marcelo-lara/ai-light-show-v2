import { createSvgIcon } from "../../utils/svg.ts";
import { ICON_REGISTRY, type IconName } from "../../svg_icons/index.ts";

export type InputState = "default" | "active";
export type InputIconPosition = "start" | "end";

export type InputBindings = {
	type?: string;
	value?: string;
	name?: string;
	placeholder?: string;
	readOnly?: boolean;
	disabled?: boolean;
	min?: number | string;
	max?: number | string;
	step?: number | string;
	inputMode?: HTMLInputElement["inputMode"];
	className?: string;
	inputClassName?: string;
	attributes?: Record<string, string>;
	dataset?: Record<string, string>;
	onInput?: (event: Event, input: HTMLInputElement) => void;
	onChange?: (event: Event, input: HTMLInputElement) => void;
	onFocus?: (event: FocusEvent, input: HTMLInputElement) => void;
	onBlur?: (event: FocusEvent, input: HTMLInputElement) => void;
};

export type InputProps = {
	caption?: string;
	icon?: IconName;
	state?: InputState;
	"icon-position"?: InputIconPosition;
	bindings?: InputBindings;
};

export type InputControl = {
	root: HTMLElement;
	input: HTMLInputElement;
	setValue: (value: string) => void;
};

export function Input(props: InputProps): InputControl {
	const root = document.createElement(props.caption ? "label" : "div");
	const rootClassName = props.bindings?.className ? ` ${props.bindings.className}` : "";
	root.className = `input-control${rootClassName}`;

	if (props.caption) {
		const caption = document.createElement("span");
		caption.className = "input-control-label";
		caption.textContent = props.caption;
		root.appendChild(caption);
	}

	const stateClass = props.state === "active" ? " is-input-active" : "";
	const iconPositionClass = props["icon-position"] === "end" ? " u-row-reverse" : "";
	const shell = document.createElement("span");
	shell.className = `input-shell${iconPositionClass}${stateClass}`;

	if (props.icon) {
		shell.appendChild(createSvgIcon(ICON_REGISTRY[props.icon], "input-shell-icon"));
	}

	const input = document.createElement("input");
	input.type = props.bindings?.type ?? "text";
	input.value = props.bindings?.value ?? "";
	input.readOnly = Boolean(props.bindings?.readOnly);
	input.disabled = Boolean(props.bindings?.disabled);
	input.className = `input-field${props.bindings?.inputClassName ? ` ${props.bindings.inputClassName}` : ""}`;
	if (props.bindings?.name) input.name = props.bindings.name;
	if (props.bindings?.placeholder) input.placeholder = props.bindings.placeholder;
	if (props.bindings?.min !== undefined) input.min = String(props.bindings.min);
	if (props.bindings?.max !== undefined) input.max = String(props.bindings.max);
	if (props.bindings?.step !== undefined) input.step = String(props.bindings.step);
	if (props.bindings?.inputMode) input.inputMode = props.bindings.inputMode;

	for (const [name, value] of Object.entries(props.bindings?.attributes ?? {})) {
		input.setAttribute(name, value);
	}
	for (const [name, value] of Object.entries(props.bindings?.dataset ?? {})) {
		input.dataset[name] = value;
	}

	input.addEventListener("input", (event) => props.bindings?.onInput?.(event, input));
	input.addEventListener("change", (event) => props.bindings?.onChange?.(event, input));
	input.addEventListener("focus", (event) => props.bindings?.onFocus?.(event, input));
	input.addEventListener("blur", (event) => props.bindings?.onBlur?.(event, input));

	shell.appendChild(input);
	root.appendChild(shell);

	return {
		root,
		input,
		setValue: (value: string) => {
			input.value = value;
		},
	};
}
import { createSvgIcon } from "../../utils/svg.ts";
import { ICON_REGISTRY, type IconName } from "../../svg_icons/index.ts";

export type ButtonState = "default" | "primary" | "active";
export type ButtonIconPosition = "start" | "end";

export type ButtonBindings = {
	title?: string;
	disabled?: boolean;
	attributes?: Record<string, string>;
	dataset?: Record<string, string>;
	onClick?: (event: MouseEvent) => void;
};

export type ButtonProps = {
	caption?: string;
	icon?: IconName;
	state?: ButtonState;
	"icon-position"?: ButtonIconPosition;
	bindings?: ButtonBindings;
};

export function Button(props: ButtonProps): HTMLButtonElement {
	const button = document.createElement("button");
	button.type = "button";

	const stateClass = props.state && props.state !== "default" ? ` ${props.state}` : "";
	button.className = `btn${stateClass}`;
	button.disabled = Boolean(props.bindings?.disabled);

	for (const [name, value] of Object.entries(props.bindings?.attributes ?? {})) {
		button.setAttribute(name, value);
	}
	for (const [name, value] of Object.entries(props.bindings?.dataset ?? {})) {
		button.dataset[name] = value;
	}

	const label = props.bindings?.title ?? props.caption ?? "";
	if (label) {
		button.title = label;
		button.setAttribute("aria-label", label);
	}

	const content = document.createElement("span");
	content.className = `btn-content btn-content--${props["icon-position"] ?? "start"}`;

	if (props.icon) {
		content.appendChild(createSvgIcon(ICON_REGISTRY[props.icon], "btn-icon"));
	}
	if (props.caption) {
		const caption = document.createElement("span");
		caption.className = "btn-caption";
		caption.textContent = props.caption;
		content.appendChild(caption);
	}

	button.appendChild(content);
	button.addEventListener("click", (event) => props.bindings?.onClick?.(event));
	return button;
}
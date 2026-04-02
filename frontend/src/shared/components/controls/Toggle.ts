import { createSvgIcon } from "../../utils/svg.ts";
import { ICON_REGISTRY } from "../../svg_icons/index.ts";

type ToggleTooltipElement = HTMLDivElement & {
	showPopover?: () => void;
	hidePopover?: () => void;
	matches: (selector: string) => boolean;
};

let toggleTooltipCount = 0;

function placeTooltip(trigger: HTMLElement, tooltip: HTMLElement): void {
	const rect = trigger.getBoundingClientRect();
	const tooltipWidth = tooltip.offsetWidth;
	const tooltipHeight = tooltip.offsetHeight;
	const left = Math.min(
		window.innerWidth - tooltipWidth / 2 - 16,
		Math.max(tooltipWidth / 2 + 16, rect.left + rect.width / 2),
	);
	const top = Math.max(tooltipHeight + 16, rect.top - 6);
	tooltip.style.left = `${left}px`;
	tooltip.style.top = `${top}px`;
}

function showTooltip(trigger: HTMLElement, tooltip: ToggleTooltipElement): void {
	if (!tooltip.matches(":popover-open")) {
		tooltip.showPopover?.();
	}
	placeTooltip(trigger, tooltip);
}

function hideTooltip(tooltip: ToggleTooltipElement): void {
	if (tooltip.matches(":popover-open")) {
		tooltip.hidePopover?.();
	}
}

export type ToggleProps = {
	label: string;
	checked: boolean;
	description?: string;
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
	text.className = "toggle-label";
	text.textContent = props.label;

	const input = document.createElement("input");
	input.type = "checkbox";
	input.checked = props.checked;
	input.addEventListener("change", () => props.onChange?.(input.checked));

	label.append(input, text);

	if (props.description) {
		const help = document.createElement("span");
		help.className = "toggle-help";

		const tooltipId = `toggle-tooltip-${toggleTooltipCount++}`;
		const trigger = document.createElement("button");
		trigger.type = "button";
		trigger.className = "toggle-help-trigger";
		trigger.setAttribute("aria-label", `${props.label} description`);
		trigger.setAttribute("aria-describedby", tooltipId);
		trigger.appendChild(createSvgIcon(ICON_REGISTRY.question, "toggle-help-icon"));

		const tooltip = document.createElement("div") as ToggleTooltipElement;
		tooltip.id = tooltipId;
		tooltip.className = "toggle-tooltip";
		tooltip.setAttribute("popover", "manual");
		tooltip.setAttribute("role", "tooltip");
		tooltip.textContent = props.description;

		const handleResize = () => placeTooltip(trigger, tooltip);

		const hideOnLeave = (event: MouseEvent | FocusEvent) => {
			const relatedTarget = event.relatedTarget;
			if (relatedTarget instanceof Node && (trigger.contains(relatedTarget) || tooltip.contains(relatedTarget))) {
				return;
			}
			hideTooltip(tooltip);
			window.removeEventListener("resize", handleResize);
		};

		trigger.addEventListener("mouseenter", () => {
			showTooltip(trigger, tooltip);
			window.addEventListener("resize", handleResize);
		});
		trigger.addEventListener("mouseleave", hideOnLeave);
		trigger.addEventListener("focusin", () => {
			showTooltip(trigger, tooltip);
			window.addEventListener("resize", handleResize);
		});
		trigger.addEventListener("focusout", hideOnLeave);
		trigger.addEventListener("keydown", (event) => {
			if (event.key === "Escape") {
				hideTooltip(tooltip);
				window.removeEventListener("resize", handleResize);
			}
		});

		tooltip.addEventListener("mouseenter", () => {
			showTooltip(trigger, tooltip);
			window.addEventListener("resize", handleResize);
		});
		tooltip.addEventListener("mouseleave", hideOnLeave);

		help.append(trigger, tooltip);
		help.addEventListener("click", (event) => {
			event.preventDefault();
			event.stopPropagation();
		});
		label.appendChild(help);
	}

	return {
		root: label,
		input,
		setChecked: (checked) => {
			input.checked = checked;
		},
	};
}

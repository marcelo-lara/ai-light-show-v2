export type TimePositionControl = {
	root: HTMLDivElement;
	input: HTMLInputElement;
	setValue: (next: string) => void;
};

export function time_position(value: string, ariaLabel = "Song position"): TimePositionControl {
	const root = document.createElement("div");
	root.className = "time_position";

	const input = document.createElement("input");
	input.type = "text";
	input.readOnly = true;
	input.value = value;
	input.className = "time_position-input";
	input.setAttribute("aria-label", ariaLabel);

	root.append(input);

	return {
		root,
		input,
		setValue: (next: string) => {
			input.value = next;
		},
	};
}

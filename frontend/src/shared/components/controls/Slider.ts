export type SliderProps = {
	label: string;
	min: number;
	max: number;
	value: number;
	step?: number;
	onInput?: (value: number) => void;
	onCommit?: (value: number) => void;
};

export function Slider(props: SliderProps): HTMLElement {
	const wrap = document.createElement("label");
	wrap.className = "slider-row";

	const title = document.createElement("span");
	title.textContent = props.label;

	const value = document.createElement("span");
	value.className = "mono";
	value.textContent = String(props.value);

	const input = document.createElement("input");
	input.type = "range";
	input.min = String(props.min);
	input.max = String(props.max);
	input.step = String(props.step ?? 1);
	input.value = String(props.value);

	input.addEventListener("input", () => {
		const next = Number(input.value);
		value.textContent = String(next);
		props.onInput?.(next);
	});

	input.addEventListener("change", () => {
		props.onCommit?.(Number(input.value));
	});

	wrap.append(title, value, input);
	return wrap;
}

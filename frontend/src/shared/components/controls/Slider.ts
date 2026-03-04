export type SliderProps = {
  label?: string;
  min: number;
  max: number;
  step: number;
  value: number;
  onInput: (value: number) => void;
  className?: string;
};

export function Slider(props: SliderProps): HTMLElement {
  const container = document.createElement("label");
  container.className = `slider-row ${props.className ?? ""}`;

  if (props.label) {
    const labelText = document.createElement("span");
    labelText.textContent = props.label;
    container.appendChild(labelText);
  }

  const input = document.createElement("input");
  input.type = "range";
  input.min = String(props.min);
  input.max = String(props.max);
  input.step = String(props.step);
  input.value = String(props.value);

  input.addEventListener("input", () => {
    props.onInput(Number(input.value));
  });

  container.appendChild(input);

  // Expose the input element for direct manipulation if needed
  (container as any).input = input;

  return container;
}

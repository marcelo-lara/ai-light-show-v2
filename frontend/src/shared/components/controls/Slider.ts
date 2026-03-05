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

  const valueDisplay = document.createElement("div");
  valueDisplay.className = "slider-value";
  valueDisplay.textContent = String(props.value);

  const updateFill = () => {
    const percent = ((Number(input.value) - props.min) / (props.max - props.min)) * 100;
    input.style.setProperty("--slider-fill", `${percent}%`);
    valueDisplay.textContent = input.value;
  };

  input.addEventListener("input", () => {
    updateFill();
    props.onInput(Number(input.value));
  });

  // Initial fill state
  updateFill();

  container.appendChild(input);
  container.appendChild(valueDisplay);

  // Expose the input element for direct manipulation if needed
  (container as any).input = input;

  return container;
}

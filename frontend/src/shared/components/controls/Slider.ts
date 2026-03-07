export type SliderProps = {
  label?: string;
  min: number;
  max: number;
  step: number;
  value: number;
  onInput: (value: number) => void;
  onCommit?: (value: number) => void;
  className?: string;
};

export function Slider(props: SliderProps): HTMLElement {
  const container = document.createElement("label");
  container.className = `slider-row ${props.className ?? ""}`;
  let isDragging = false;

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

  input.addEventListener("mousedown", () => { isDragging = true; });
  input.addEventListener("touchstart", () => { isDragging = true; }, { passive: true });
  
  const endDrag = () => {
    if (isDragging) {
      isDragging = false;
      if (props.onCommit) props.onCommit(Number(input.value));
    }
  };

  window.addEventListener("mouseup", endDrag);
  window.addEventListener("touchend", endDrag);

  input.addEventListener("input", () => {
    updateFill();
    props.onInput(Number(input.value));
  });

  // Method to update value from outside only if not dragging
  (container as any).setValue = (val: number) => {
    if (!isDragging) {
      input.value = String(val);
      updateFill();
    }
  };

  // Initial fill state
  updateFill();

  container.appendChild(input);
  container.appendChild(valueDisplay);

  return container;
}



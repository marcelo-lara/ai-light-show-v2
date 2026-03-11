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

export type SliderControl = {
  root: HTMLLabelElement;
  input: HTMLInputElement;
  setValue: (value: number) => void;
  dispose: () => void;
};

export function Slider(props: SliderProps): SliderControl {
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

  const onMouseDown = () => {
    isDragging = true;
  };
  const onTouchStart = () => {
    isDragging = true;
  };

  const endDrag = () => {
    if (isDragging) {
      isDragging = false;
      if (props.onCommit) props.onCommit(Number(input.value));
    }
  };

  const onInput = () => {
    updateFill();
    props.onInput(Number(input.value));
  };

  input.addEventListener("mousedown", onMouseDown);
  input.addEventListener("touchstart", onTouchStart, { passive: true });
  window.addEventListener("mouseup", endDrag);
  window.addEventListener("touchend", endDrag);
  input.addEventListener("input", onInput);

  // Initial fill state
  updateFill();

  container.appendChild(input);
  container.appendChild(valueDisplay);

  const setValue = (val: number) => {
    if (!isDragging) {
      input.value = String(val);
      updateFill();
    }
  };

  const dispose = () => {
    input.removeEventListener("mousedown", onMouseDown);
    input.removeEventListener("touchstart", onTouchStart);
    input.removeEventListener("input", onInput);
    window.removeEventListener("mouseup", endDrag);
    window.removeEventListener("touchend", endDrag);
  };

  return { root: container, input, setValue, dispose };
}

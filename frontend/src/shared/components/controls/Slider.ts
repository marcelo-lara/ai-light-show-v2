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
  container.className = `slider-row${props.label ? " has-label" : ""}${props.className ? ` ${props.className}` : ""}`;
  let isDragging = false;
  let isEditing = false;
  let editStartValue = String(props.value);

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

  const valueSlot = document.createElement("div");
  valueSlot.className = "slider-value-slot";

  const valueDisplay = document.createElement("div");
  valueDisplay.className = "slider-value";
  valueDisplay.textContent = String(props.value);
  valueDisplay.tabIndex = 0;
  valueDisplay.setAttribute("role", "button");
  valueDisplay.setAttribute("aria-label", props.label ? `Edit ${props.label} value` : "Edit slider value");

  const valueInput = document.createElement("input");
  valueInput.type = "text";
  valueInput.className = "slider-value-input";
  valueInput.value = String(props.value);
  valueInput.inputMode = [props.min, props.max, props.step].some((value) => !Number.isInteger(value)) ? "decimal" : "numeric";
  valueInput.setAttribute("aria-label", props.label ? `Enter ${props.label} value` : "Enter slider value");

  const getPrecision = (value: number) => {
    const text = String(value);
    if (!text.includes(".")) return 0;
    return text.split(".")[1]?.length ?? 0;
  };

  const clampValue = (value: number) => Math.min(props.max, Math.max(props.min, value));

  const normalizeValue = (value: number) => {
    const clamped = clampValue(value);
    if (props.step <= 0) return clamped;
    const steps = Math.round((clamped - props.min) / props.step);
    const aligned = props.min + steps * props.step;
    const precision = Math.max(getPrecision(props.min), getPrecision(props.max), getPrecision(props.step));
    return Number(clampValue(aligned).toFixed(precision));
  };

  const syncValueText = () => {
    valueDisplay.textContent = input.value;
    if (!isEditing) valueInput.value = input.value;
  };

  const updateFill = () => {
    const percent = ((Number(input.value) - props.min) / (props.max - props.min)) * 100;
    input.style.setProperty("--slider-fill", `${percent}%`);
    syncValueText();
  };

  const exitEditMode = () => {
    isEditing = false;
    valueInput.classList.remove("is-editing", "is-invalid");
    valueDisplay.classList.remove("is-hidden");
    valueInput.value = input.value;
  };

  const beginEditMode = () => {
    if (isDragging || isEditing) return;
    isEditing = true;
    editStartValue = input.value;
    valueInput.value = input.value;
    valueDisplay.classList.add("is-hidden");
    valueInput.classList.add("is-editing");
    valueInput.focus();
    valueInput.select();
  };

  const discardEdit = () => {
    valueInput.value = editStartValue;
    exitEditMode();
  };

  const commitEdit = () => {
    const nextValue = Number(valueInput.value.trim());
    if (!Number.isFinite(nextValue)) {
      valueInput.classList.add("is-invalid");
      valueInput.select();
      return;
    }
    const normalizedValue = normalizeValue(nextValue);
    input.value = String(normalizedValue);
    exitEditMode();
    updateFill();
    props.onInput(normalizedValue);
    props.onCommit?.(normalizedValue);
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

  const onValueDisplayPointerDown = (event: MouseEvent) => {
    event.preventDefault();
  };

  const onValueDisplayClick = (event: MouseEvent) => {
    event.preventDefault();
    beginEditMode();
  };

  const onValueDisplayKeyDown = (event: KeyboardEvent) => {
    if (event.key !== "Enter" && event.key !== " ") return;
    event.preventDefault();
    beginEditMode();
  };

  const onValueInputKeyDown = (event: KeyboardEvent) => {
    if (event.key === "Enter") {
      event.preventDefault();
      commitEdit();
      return;
    }
    if (event.key === "Escape") {
      event.preventDefault();
      discardEdit();
    }
  };

  const onValueInputBlur = () => {
    if (!isEditing) return;
    discardEdit();
  };

  const onValueInputPointerDown = (event: MouseEvent) => {
    event.preventDefault();
    valueInput.focus();
  };

  input.addEventListener("mousedown", onMouseDown);
  input.addEventListener("touchstart", onTouchStart, { passive: true });
  window.addEventListener("mouseup", endDrag);
  window.addEventListener("touchend", endDrag);
  input.addEventListener("input", onInput);
  valueDisplay.addEventListener("mousedown", onValueDisplayPointerDown);
  valueDisplay.addEventListener("click", onValueDisplayClick);
  valueDisplay.addEventListener("keydown", onValueDisplayKeyDown);
  valueInput.addEventListener("mousedown", onValueInputPointerDown);
  valueInput.addEventListener("keydown", onValueInputKeyDown);
  valueInput.addEventListener("blur", onValueInputBlur);

  // Initial fill state
  updateFill();

  container.appendChild(input);
  valueSlot.appendChild(valueDisplay);
  valueSlot.appendChild(valueInput);
  container.appendChild(valueSlot);

  const setValue = (val: number) => {
    if (!isDragging && !isEditing) {
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
    valueDisplay.removeEventListener("mousedown", onValueDisplayPointerDown);
    valueDisplay.removeEventListener("click", onValueDisplayClick);
    valueDisplay.removeEventListener("keydown", onValueDisplayKeyDown);
    valueInput.removeEventListener("mousedown", onValueInputPointerDown);
    valueInput.removeEventListener("keydown", onValueInputKeyDown);
    valueInput.removeEventListener("blur", onValueInputBlur);
  };

  return { root: container, input, setValue, dispose };
}

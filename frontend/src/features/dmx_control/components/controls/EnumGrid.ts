type EnumOption = {
  label: string;
  value: string;
};

export type EnumGridHandle = {
  root: HTMLElement;
  setValue: (value: string) => void;
  dispose: () => void;
};

export function EnumGrid(options: {
  label: string;
  options: EnumOption[];
  value: string;
  onChange: (value: string) => void;
}): EnumGridHandle {
  const root = document.createElement("div");
  root.className = "enum-grid";

  const label = document.createElement("label");
  label.className = "enum-grid-label";
  label.textContent = options.label;

  const grid = document.createElement("div");
  grid.className = "enum-grid-options";

  const buttons: HTMLButtonElement[] = [];
  let currentValue = options.value;

  const sync = () => {
    for (const button of buttons) {
      const selected = button.dataset.value === currentValue;
      button.classList.toggle("selected", selected);
      button.setAttribute("aria-pressed", selected ? "true" : "false");
    }
  };

  for (const option of options.options) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "enum-grid-option";
    button.dataset.value = option.value;
    button.title = option.label;
    button.setAttribute("aria-label", option.label);
    button.addEventListener("click", () => {
      currentValue = option.value;
      sync();
      options.onChange(option.value);
    });
    buttons.push(button);
    grid.appendChild(button);
  }

  sync();
  root.append(label, grid);

  return {
    root,
    setValue: (value) => {
      currentValue = value;
      sync();
    },
    dispose: () => {},
  };
}

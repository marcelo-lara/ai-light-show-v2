import { Button } from "../../../../shared/components/controls/Button.ts";

type EnumOption = {
  label: string;
  value: string;
  swatch?: string;
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

  const buttons: Array<{ element: HTMLButtonElement; value: string }> = [];
  let currentValue = options.value;

  const sync = () => {
    for (const button of buttons) {
      const selected = button.value === currentValue;
      button.element.classList.toggle("is-selected", selected);
      button.element.setAttribute("aria-pressed", selected ? "true" : "false");
    }
  };

  for (const option of options.options) {
    const button = Button({
      caption: option.swatch ? undefined : option.label,
      state: "default",
      bindings: {
        className: "enum-grid-option",
        title: option.label,
        dataset: { value: option.value },
        attributes: { "aria-pressed": "false" },
        onClick: () => {
          currentValue = option.value;
          sync();
          options.onChange(option.value);
        },
      },
    });
    if (!option.swatch) {
      button.querySelector(".btn-content")?.classList.add("enum-grid-option-content");
    }
    if (option.swatch) {
      button.style.background = option.swatch;
      button.classList.add("enum-grid-option-swatch");
      button.querySelector(".btn-content")?.remove();
    }
    buttons.push({ element: button, value: option.value });
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

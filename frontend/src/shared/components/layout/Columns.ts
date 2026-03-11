export type ColumnsOptions = {
  className?: string;
  leftColPx?: number;
};

export function Columns(left: HTMLElement, right: HTMLElement, options: ColumnsOptions = {}): HTMLElement {
  const root = document.createElement("div");
  root.className = `columns ${options.className ?? ""}`.trim();
  root.style.setProperty("--left-col", `${options.leftColPx ?? 280}px`);
  root.append(left, right);
  return root;
}

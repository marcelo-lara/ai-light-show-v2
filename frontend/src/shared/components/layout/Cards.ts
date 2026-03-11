export type CardsOptions = {
  className?: string;
};

export function Cards(children: HTMLElement[], options: CardsOptions = {}): HTMLElement {
  const root = document.createElement("div");
  root.className = `cards ${options.className ?? ""}`.trim();
  root.append(...children);
  return root;
}


export type ThemeId = "dark" | "tokyo-dark" | "light";

const KEY = "dmx_ui_theme";

let theme: ThemeId = "dark";
const listeners = new Set<() => void>();

export function getTheme(): ThemeId {
  return theme;
}

export function subscribeTheme(fn: () => void) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

function emit() {
  for (const fn of listeners) fn();
}

/**
 * Apply theme by setting <html data-theme="...">.
 * Call initTheme() as early as possible (before UI mounts) to avoid flashes.
 */
export function applyTheme(t: ThemeId) {
  theme = t;
  document.documentElement.setAttribute("data-theme", t);
  try {
    localStorage.setItem(KEY, t);
  } catch {
    // ignore storage errors (private mode, etc.)
  }
  emit();
}

export function initTheme() {
  let saved: ThemeId | null = null;

  try {
    const raw = localStorage.getItem(KEY) as ThemeId | null;
    if (raw === "dark" || raw === "tokyo-dark" || raw === "light") saved = raw;
  } catch {
    // ignore
  }

  applyTheme(saved ?? "dark");
}

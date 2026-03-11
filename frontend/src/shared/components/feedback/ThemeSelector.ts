import { applyTheme, getTheme, type ThemeId } from "../../state/theme_state.ts";

export const THEMES: Array<{ id: ThemeId; label: string }> = [
  { id: "dark", label: "Dark" },
  { id: "tokyo-dark", label: "Tokyo Dark" },
  { id: "light", label: "Light" },
];

/**
 * Logic-only model for a theme selector UI.
 * Copilot should render this as a dropdown or segmented control in UIX.
 */
export function getThemeModel() {
  return {
    current: getTheme(),
    themes: THEMES,
    setTheme: (t: ThemeId) => applyTheme(t),
  };
}

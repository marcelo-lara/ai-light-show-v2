import { selectArmedCount, selectEditLock, selectPlayback, selectShowState } from "../../state/selectors.ts";
import { formatTimeMs } from "../../utils/format.ts";
import { Card } from "../layout/Card.ts";
import { Badge } from "./Badge.ts";
import { getBackendStore } from "../../state/backend_state.ts";
import { getThemeModel } from "./ThemeSelector.ts";

/**
 * Render-only module.
 * Implement actual UIX view code where appropriate; for now this provides a stable model.
 */
export function getStatusModel() {
  const wsState = ((globalThis as any).__WS_STATE__ ?? "disconnected") as string;

  const showState = selectShowState(); // verbatim from backend or "unknown"
  const playback = selectPlayback();
  const editLock = selectEditLock();
  const arm = selectArmedCount();

  const llm = ((globalThis as any).__LLM_STATE__ ?? { status: "idle" }) as { status: string };

  return {
    ws: wsState,
    show: showState,
    playback: {
      state: playback.state,
      time: formatTimeMs(playback.time_ms),
      section: playback.section_name,
      bpm: playback.bpm,
    },
    edits: editLock === null ? "unknown" : (editLock ? "locked" : "unlocked"),
    arm: `${arm.armed}/${arm.total}`,
    llm: llm.status,
    stale: getBackendStore().stale,
  };
}

export function StatusCard(): HTMLElement {
  const model = getStatusModel();

  const content = document.createElement("div");
  content.className = "status-grid";

  content.appendChild(row("WS", Badge(model.ws, wsTone(model.ws))));
  content.appendChild(row("Show", Badge(cap(model.show), showTone(model.show))));
  content.appendChild(row("Playback", Badge(`${cap(model.playback.state)} @ ${model.playback.time}`, playbackTone(model.playback.state))));
  content.appendChild(row("Edits", Badge(cap(model.edits), model.edits === "locked" ? "warn" : "ok")));
  content.appendChild(row("ARM", Badge(model.arm, "default")));
  content.appendChild(row("LLM", Badge(cap(model.llm), llmTone(model.llm))));
  content.appendChild(row("Sync", Badge(model.stale ? "Stale" : "Live", model.stale ? "warn" : "ok")));

  const themeRow = document.createElement("label");
  themeRow.className = "status-row";
  const themeText = document.createElement("span");
  themeText.textContent = "Theme";
  const themeSelect = document.createElement("select");
  themeSelect.className = "theme-select";
  const themeModel = getThemeModel();
  for (const theme of themeModel.themes) {
    const option = document.createElement("option");
    option.value = theme.id;
    option.textContent = theme.label;
    option.selected = theme.id === themeModel.current;
    themeSelect.appendChild(option);
  }
  themeSelect.addEventListener("change", () => themeModel.setTheme(themeSelect.value as any));
  themeRow.append(themeText, themeSelect);
  content.appendChild(themeRow);

  return Card(content, { title: "Status" });
}

function row(label: string, value: HTMLElement): HTMLElement {
  const wrapper = document.createElement("div");
  wrapper.className = "status-row";
  const left = document.createElement("span");
  left.textContent = label;
  wrapper.append(left, value);
  return wrapper;
}

function wsTone(value: string) {
  if (value === "connected") return "ok";
  if (value === "connecting" || value === "reconnecting") return "warn";
  return "err";
}

function showTone(value: string) {
  if (value === "running") return "ok";
  if (value === "idle") return "default";
  return "warn";
}

function playbackTone(value: string) {
  if (value === "playing") return "ok";
  if (value === "paused") return "warn";
  if (value === "stopped") return "default";
  return "warn";
}

function llmTone(value: string) {
  if (value === "streaming") return "ok";
  if (value === "error") return "err";
  return "default";
}

function cap(value: string) {
  if (!value) return "Unknown";
  return value.charAt(0).toUpperCase() + value.slice(1);
}

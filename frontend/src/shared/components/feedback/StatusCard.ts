import { selectArmedCount, selectEditLock, selectPlayback, selectShowState } from "../../state/selectors.ts";
import { formatTimeMs } from "../../utils/format.ts";
import { Card } from "../layout/Card.ts";
import { Badge } from "./Badge.ts";
import { getBackendStore, subscribeBackendStore } from "../../state/backend_state.ts";
import { getThemeModel } from "./ThemeSelector.ts";
import { subscribeTheme } from "../../state/theme_state.ts";
import { getWsState, subscribeWsState } from "../../state/ws_state.ts";

/**
 * Render-only module.
 * Implement actual UIX view code where appropriate; for now this provides a stable model.
 */
export function getStatusModel() {
  const wsState = getWsState();

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
  const content = document.createElement("div");
  content.className = "status-grid";

  const showBadge = Badge("", "default");
  const wsBadge = Badge("", "default");
  const playbackBadge = Badge("", "default");
  const syncBadge = Badge("", "default");
  const editsBadge = Badge("", "default");
  const llmBadge = Badge("", "default");
  const armBadge = Badge("", "default");

  const showRow = row("Show", showBadge);
  const wsRow = row("WS", wsBadge);
  const playbackRow = row("Playback", playbackBadge);
  const syncRow = row("Sync", syncBadge);
  const editsRow = row("Edits", editsBadge);
  const llmRow = row("LLM", llmBadge);
  const armRow = row("ARM", armBadge);

  content.appendChild(showRow);
  content.appendChild(wsRow);
  content.appendChild(playbackRow);
  content.appendChild(syncRow);
  content.appendChild(editsRow);
  content.appendChild(llmRow);
  content.appendChild(armRow);

  const themeRow = document.createElement("label");
  themeRow.className = "status-row status-row-theme";
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

  const render = () => {
    const model = getStatusModel();
    const show = getShowState(model.ws, model.show);
    const playback = getPlaybackState(model.ws, model.playback.state, model.playback.time);
    const sync = getSyncState(model.ws, model.stale);
    const disconnected = model.ws === "disconnected";

    showRow.hidden = disconnected;
    playbackRow.hidden = disconnected;
    syncRow.hidden = disconnected;
    editsRow.hidden = disconnected;
    llmRow.hidden = disconnected;
    armRow.hidden = disconnected;

    setBadge(showBadge, show.label, show.tone);
    setBadge(wsBadge, model.ws, wsTone(model.ws));
    setBadge(playbackBadge, playback.label, playback.tone);
    setBadge(syncBadge, sync.label, sync.tone);
    setBadge(editsBadge, cap(model.edits), model.edits === "locked" ? "warn" : "ok");
    setBadge(llmBadge, cap(model.llm), llmTone(model.llm));
    setBadge(armBadge, model.arm, "default");
    themeSelect.value = getThemeModel().current;
  };

  const unsubscribeBackend = subscribeBackendStore(render);
  const unsubscribeWs = subscribeWsState(render);
  const unsubscribeTheme = subscribeTheme(render);
  render();

  const card = Card(content, { className: "status-card" });
  (card as unknown as { _cleanup: () => void })._cleanup = () => {
    unsubscribeBackend();
    unsubscribeWs();
    unsubscribeTheme();
  };
  return card;
}

function row(label: string, value: HTMLElement): HTMLElement {
  const wrapper = document.createElement("div");
  wrapper.className = "status-row";
  const left = document.createElement("span");
  left.textContent = label;
  wrapper.append(left, value);
  return wrapper;
}

function setBadge(node: HTMLElement, label: string, tone: "default" | "ok" | "warn" | "err") {
  node.className = `badge ${tone}`;
  node.textContent = label;
}

function getSyncState(ws: string, stale: boolean): { label: string; tone: "default" | "ok" | "warn" | "err" } {
  if (ws === "disconnected") return { label: "Disconnected", tone: "err" };
  if (ws === "connecting" || ws === "reconnecting") return { label: "Connecting", tone: "warn" };
  if (stale) return { label: "Stale", tone: "warn" };
  return { label: "Connected", tone: "ok" };
}

function getShowState(ws: string, show: string): { label: string; tone: "default" | "ok" | "warn" | "err" } {
  if (ws === "disconnected") return { label: "Offline", tone: "err" };
  if (ws === "connecting" || ws === "reconnecting") return { label: "Pending", tone: "warn" };
  return { label: cap(show), tone: showTone(show) };
}

function getPlaybackState(
  ws: string,
  playbackState: string,
  playbackTime: string,
): { label: string; tone: "default" | "ok" | "warn" | "err" } {
  if (ws === "disconnected") return { label: "Offline", tone: "err" };
  if (ws === "connecting" || ws === "reconnecting") return { label: "Pending", tone: "warn" };
  return {
    label: `${cap(playbackState)} @ ${playbackTime}`,
    tone: playbackTone(playbackState),
  };
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

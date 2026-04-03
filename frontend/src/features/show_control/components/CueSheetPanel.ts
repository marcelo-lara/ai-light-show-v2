import { Card } from "../../../shared/components/layout/Card.ts";
import { List } from "../../../shared/components/layout/List.ts";
import { getBackendStore, subscribeBackendStore } from "../../../shared/state/backend_state.ts";
import type { CueEntry } from "../../../shared/transport/protocol.ts";
import { formatCueLabel, getChaserById, isChaserCue, isEffectCue } from "../../show_builder/cue_utils.ts";
import { findCurrentCueTime, formatCueTime } from "../../show_builder/components/cue_sheet/format.ts";

function cueLabel(cue: CueEntry): string {
  if (isEffectCue(cue)) return formatCueLabel(cue.effect);
  const chaser = getChaserById(getBackendStore().state.chasers ?? [], cue.chaser_id);
  return chaser?.name ?? formatCueLabel(cue.chaser_id);
}

function cueMeta(cue: CueEntry): string {
  if (isEffectCue(cue)) return formatCueLabel(cue.fixture_id);
  return "Chaser";
}

export function CueSheetPanel(): HTMLElement {
  const content = document.createElement("div");
  content.className = "show-control-body";
  const list = document.createElement("div");
  list.className = "show-control-list o-list";
  content.appendChild(list);

  const render = () => {
    const state = getBackendStore().state;
    const cues = state.cues ?? [];
    const activeTime = findCurrentCueTime(cues, state.playback?.time_ms ?? 0);
    list.replaceChildren();

    if (cues.length === 0) {
      const empty = document.createElement("span");
      empty.className = "show-control-label u-cell u-cell-effect";
      empty.textContent = "No cues loaded";
      list.appendChild(List({ className: "cue-sheet-row", content: empty, isActive: true }));
      return;
    }

    for (const cue of cues) {
      const time = document.createElement("span");
      time.className = "u-cell u-cell-time";
      time.textContent = formatCueTime(cue.time);

      const title = document.createElement("span");
      title.className = "cue-sheet-title u-cell u-cell-effect";
      title.textContent = cueLabel(cue);

      const meta = document.createElement("span");
      meta.className = "cue-sheet-meta muted";
      meta.textContent = cueMeta(cue);

      list.appendChild(List({
        className: "cue-sheet-row",
        content: [time, title, meta],
        isActive: activeTime !== null && Math.abs(cue.time - activeTime) < 1e-6,
        title: JSON.stringify(cue.data ?? {}),
      }));
    }
  };

  render();
  const card = Card(content, { variant: "outlined", className: "show-control-panel" });
  (card as unknown as { _cleanup: () => void })._cleanup = subscribeBackendStore(render);
  return card;
}

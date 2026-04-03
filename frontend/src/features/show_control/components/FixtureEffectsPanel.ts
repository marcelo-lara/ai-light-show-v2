import { Card } from "../../../shared/components/layout/Card.ts";
import { List } from "../../../shared/components/layout/List.ts";
import { getBackendStore, subscribeBackendStore } from "../../../shared/state/backend_state.ts";
import { isEffectCue, formatCueLabel } from "../../show_builder/cue_utils.ts";
import { findCurrentCueTime, formatCueTime } from "../../show_builder/components/cue_sheet/format.ts";

export function FixtureEffectsPanel(): HTMLElement {
  const content = document.createElement("div");
  content.className = "show-control-body";

  const list = document.createElement("div");
  list.className = "fixture-effects-list o-list";
  content.appendChild(list);

  const render = () => {
    const state = getBackendStore().state;
    const effects = (state.cues ?? []).filter(isEffectCue);
    const activeTime = findCurrentCueTime(effects, state.playback?.time_ms ?? 0);
    list.replaceChildren();

    if (effects.length === 0) {
      const empty = document.createElement("span");
      empty.className = "fixture-effects-row-details u-cell u-cell-effect";
      empty.textContent = "No effect cues loaded";
      list.appendChild(List({ className: "fixture-effects-row", content: empty, isActive: true }));
      return;
    }

    for (const cue of effects) {
      const time = document.createElement("span");
      time.className = "u-cell u-cell-time";
      time.textContent = formatCueTime(cue.time);

      const details = document.createElement("span");
      details.className = "fixture-effects-row-details u-cell u-cell-effect";
      details.textContent = `${formatCueLabel(cue.fixture_id)} ${formatCueLabel(cue.effect)}`;

      const duration = document.createElement("span");
      duration.className = "cue-sheet-meta muted";
      duration.textContent = `${cue.duration.toFixed(1)}s`;

      list.appendChild(List({
        className: "fixture-effects-row",
        content: [time, details, duration],
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

import { selectArmedCount, selectEditLock, selectPlayback, selectShowState } from "../../state/selectors.ts";
import { formatTimeMs } from "../../utils/format.ts";

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
  };
}

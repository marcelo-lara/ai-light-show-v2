import { initBackendState, applyPatch, applySnapshot, getBackendStore } from "../shared/state/backend_state.ts";
import { initTheme } from "../shared/state/theme_state.ts";
import { setWsState } from "../shared/state/ws_state.ts";
import { WsClient } from "../shared/transport/ws_client.ts";
import type { ConnectionState, WsInbound } from "../shared/transport/protocol.ts";
import {
  addActionProposal,
  addSystemMessage,
  appendStreamingChunk,
  clearConversationState,
  failStreaming,
  finishStreaming,
  resolveActionProposal,
  upsertSystemStatus,
} from "../features/llm_chat/llm_state.ts";
import { ConfirmCancelPrompt } from "../shared/components/feedback/ConfirmCancelPrompt.ts";
import { enqueueAnalyzerItem, executeAllAnalyzerItems } from "../features/song_analysis/song_analysis_intents.ts";
import { setSongLoaderSongs } from "../features/song_analysis/song_loader/state.ts";

// If you inject bootstrap JSON in HTML, expose it as window.__BOOTSTRAP_STATE__
declare global {
  interface Window {
    __BOOTSTRAP_STATE__?: unknown;
  }
}

export type BootContext = {
  wsUrl: string; // e.g., "ws://localhost:8000/ws"
};

type MissingArtifact = {
  artifact?: string;
  path?: string;
};

function formatMissingArtifacts(missingArtifacts: MissingArtifact[]): string {
  return missingArtifacts
    .map((artifact) => {
      const artifactName = typeof artifact?.artifact === "string" ? artifact.artifact : "artifact";
      const artifactPath = typeof artifact?.path === "string" ? artifact.path : "unknown path";
      return `${artifactName} (${artifactPath})`;
    })
    .join(", ");
}

function isMissingFeaturesArtifact(missingArtifacts: MissingArtifact[]): boolean {
  return missingArtifacts.some((artifact) => {
    if (artifact?.artifact === "features_file") {
      return true;
    }
    return typeof artifact?.path === "string" && artifact.path.endsWith("/features.json");
  });
}

export function boot(ctx: BootContext) {
  initTheme(); // apply theme ASAP to avoid FOUC
  let promptingSongDraftAnalysis = false;

  const promptToQueueAnalyzerTasks = async (helperId: string): Promise<boolean> => {
    const state = getBackendStore().state;
    const currentSong = state.song?.filename ?? "";
    const analyzer = state.analyzer ?? {};
    const taskTypes = Array.isArray(analyzer.task_types)
      ? analyzer.task_types.flatMap((taskType) => {
          if (!taskType || typeof taskType !== "object") {
            return [];
          }
          const value = (taskType as { value?: unknown }).value;
          return typeof value === "string" ? [value] : [];
        })
      : [];

    if (!currentSong || analyzer.available === false || analyzer.playback_locked === true || taskTypes.length === 0) {
      return false;
    }

    promptingSongDraftAnalysis = true;
    try {
      const confirmed = await ConfirmCancelPrompt({
        title: "Missing analyzer features",
        message: `song_draft needs features.json. Add all analyzer queue tasks for ${currentSong} and run all now?`,
        confirmLabel: "Queue + Run all",
        cancelLabel: "Cancel",
      });
      if (!confirmed) {
        return false;
      }
      for (const taskType of taskTypes) {
        enqueueAnalyzerItem(taskType, currentSong);
      }
      executeAllAnalyzerItems();
      addSystemMessage(`Queued all analyzer tasks for ${currentSong} and started run all.`, "info");
      return true;
    } finally {
      promptingSongDraftAnalysis = false;
    }
  };

  try {
    const ws = new URL(ctx.wsUrl);
    const protocol = ws.protocol === "wss:" ? "https:" : "http:";
    (globalThis as any).__BACKEND_HTTP_ORIGIN__ = `${protocol}//${ws.host}`;
  } catch {
    // ignore invalid ws url
  }

  // 1) hydration/bootstrap
  const injected = (window.__BOOTSTRAP_STATE__ ?? null) as any;
  let bootstrap = injected;

  if (!bootstrap?.state) {
    try {
      const raw = localStorage.getItem("last_snapshot");
      if (raw) bootstrap = JSON.parse(raw);
    } catch {
      // ignore storage parsing errors
    }
  }

  if (bootstrap && typeof bootstrap === "object" && bootstrap.state) {
    initBackendState(bootstrap.state, { stale: true, seq: Number(bootstrap.seq ?? 0) });
  } else {
    initBackendState(undefined, { stale: true, seq: 0 });
  }

  // 2) connect WS
  const ws = new WsClient(ctx.wsUrl, {
    onConnectionState: (s: ConnectionState) => {
      (globalThis as any).__WS_STATE__ = s;
      setWsState(s);
    },
    onMessage: (m: WsInbound) => {
      if (m.type === "snapshot") {
        applySnapshot(m);
        try {
          localStorage.setItem("last_snapshot", JSON.stringify({ seq: m.seq, state: m.state }));
        } catch {
          // ignore storage errors
        }
      } else if (m.type === "patch") {
        applyPatch(m);
      } else if (m.type === "event") {
        const data = (m.data ?? {}) as Record<string, unknown>;
        if (m.message === "song_list") {
          setSongLoaderSongs(Array.isArray(data.songs) ? data.songs.filter((song): song is string => typeof song === "string") : []);
          return;
        }
        if (data.domain === "llm") {
          if (m.message === "llm_status" && typeof data.request_id === "string" && typeof data.label === "string") {
            upsertSystemStatus(data.request_id, data.label);
            return;
          }
          if (m.message === "llm_delta" && typeof data.delta === "string") {
            appendStreamingChunk(data.delta);
            return;
          }
          if (m.message === "llm_done") {
            finishStreaming();
            return;
          }
          if (
            m.message === "llm_action_proposed" &&
            typeof data.request_id === "string" &&
            typeof data.action_id === "string" &&
            typeof data.title === "string" &&
            typeof data.summary === "string"
          ) {
            addActionProposal({
              requestId: data.request_id,
              actionId: data.action_id,
              title: data.title,
              summary: data.summary,
              toolName: typeof data.tool_name === "string" ? data.tool_name : undefined,
              arguments: typeof data.arguments === "object" && data.arguments ? (data.arguments as Record<string, unknown>) : undefined,
            });
            return;
          }
          if (
            (m.message === "llm_action_rejected" || m.message === "llm_action_applied") &&
            typeof data.request_id === "string" &&
            typeof data.action_id === "string"
          ) {
            resolveActionProposal(
              data.request_id,
              data.action_id,
              m.message === "llm_action_applied" ? "Action applied." : "Action rejected.",
              "info",
            );
            return;
          }
          if (m.message === "llm_error") {
            failStreaming(
              typeof data.request_id === "string" ? data.request_id : undefined,
              typeof data.code === "string" ? data.code : "llm_error",
              typeof data.detail === "string" ? data.detail : "The assistant request failed.",
            );
            return;
          }
          if (m.message === "llm_cancelled") {
            finishStreaming();
            return;
          }
          if (m.message === "llm_conversation_cleared") {
            clearConversationState();
            return;
          }
        }
        if (m.message === "cue_helper_apply_failed") {
          const details = m.data as {
            helper_id?: string;
            reason?: string;
            missing_artifacts?: Array<{ artifact?: string; path?: string }>;
          } | undefined;
          const helperId = typeof details?.helper_id === "string" ? details.helper_id : "cue helper";
          const reason = typeof details?.reason === "string" ? details.reason : "apply_failed";
          const missingArtifacts = Array.isArray(details?.missing_artifacts) ? details.missing_artifacts : [];
          if (missingArtifacts.length > 0) {
            const artifactSummary = formatMissingArtifacts(missingArtifacts);
            if (helperId === "song_draft" && isMissingFeaturesArtifact(missingArtifacts) && !promptingSongDraftAnalysis) {
              void promptToQueueAnalyzerTasks(helperId).then((queued) => {
                if (!queued) {
                  addSystemMessage(`Failed to apply ${helperId}: missing analyzer artifacts ${artifactSummary}`, "error");
                }
              });
              return;
            }
            addSystemMessage(`Failed to apply ${helperId}: missing analyzer artifacts ${artifactSummary}`, "error");
            return;
          }
          addSystemMessage(`Failed to apply ${helperId}: ${reason}`, "error");
          return;
        }
        if (m.level === "error") {
          addSystemMessage(m.message, "error");
        }
        if (m.message === "analyzer_item_enqueued") {
          addSystemMessage("Analyzer item added to queue.", "info");
        }
        if (m.message === "analyzer_item_removed") {
          addSystemMessage("Analyzer item removed from queue.", "info");
        }
        if (m.message === "analyzer_items_removed") {
          const count = typeof data.count === "number" ? data.count : 0;
          addSystemMessage(count > 0 ? `Removed ${count} analyzer item${count === 1 ? "" : "s"} from queue.` : "No analyzer items removed.", "info");
        }
        if (m.message === "analyzer_item_executed") {
          addSystemMessage("Analyzer item marked to run.", "info");
        }
        if (m.message === "analyzer_items_executed") {
          const count = typeof data.count === "number" ? data.count : 0;
          addSystemMessage(count > 0 ? `Queued ${count} analyzer item${count === 1 ? "" : "s"} to run.` : "No queued analyzer items to run.", "info");
        }
        if (m.message === "cue_helper_applied") {
          const data = m.data as { helper_id?: string; generated?: number; replaced?: number; skipped?: number } | undefined;
          if (data) {
            const { helper_id, generated = 0, replaced = 0, skipped = 0 } = data;
            addSystemMessage(
              `Applied ${helper_id}: ${generated} generated, ${replaced} replaced, ${skipped} skipped`,
              "info"
            );
          }
        }
      }
    },
  });

  (globalThis as any).__WS_CLIENT__ = ws;

  ws.connect({
    type: "hello",
    client: "uix-ui",
    version: "0.1",
  });

  return ws;
}

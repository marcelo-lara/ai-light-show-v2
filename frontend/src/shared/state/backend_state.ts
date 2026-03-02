import type { BackendState, PatchMsg, SnapshotMsg } from "../transport/protocol.ts";

export type BackendStore = {
  stale: boolean;
  seq: number;
  state: BackendState;
};

const EMPTY: BackendStore = { stale: true, seq: 0, state: {} };

let store: BackendStore = { ...EMPTY };
const listeners = new Set<() => void>();

export function getBackendStore(): BackendStore {
  return store;
}

export function subscribeBackendStore(fn: () => void): () => void {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

function emit() {
  for (const fn of listeners) fn();
}

export function initBackendState(initial?: BackendState, opts?: { stale?: boolean; seq?: number }) {
  store = {
    stale: opts?.stale ?? true,
    seq: opts?.seq ?? 0,
    state: initial ?? {},
  };
  emit();
}

export function applySnapshot(msg: SnapshotMsg) {
  store = {
    stale: false,
    seq: msg.seq,
    state: msg.state ?? {},
  };
  emit();
}

export function applyPatch(msg: PatchMsg) {
  if (msg.seq <= store.seq) return;

  const next = structuredClone(store.state) as BackendState;

  for (const ch of msg.changes) {
    applyPath(next as unknown as Record<string, unknown>, ch.path, ch.value);
  }

  store = { stale: store.stale, seq: msg.seq, state: next };
  emit();
}

function applyPath(root: Record<string, unknown>, path: (string | number)[], value: unknown) {
  if (path.length === 0) return;

  let cur: any = root;
  for (let i = 0; i < path.length - 1; i++) {
    const key = path[i];
    if (cur[key] === undefined || cur[key] === null) {
      cur[key] = typeof path[i + 1] === "number" ? [] : {};
    }
    cur = cur[key];
  }
  cur[path[path.length - 1]] = value;
}

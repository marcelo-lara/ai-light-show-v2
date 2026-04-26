export function formatTimeMs(ms: number): string {
  const total = Math.max(0, Math.floor(ms));
  const s = Math.floor(total / 1000);
  const m = Math.floor(s / 60);
  const ss = String(s % 60).padStart(2, "0");
  return `${m}:${ss}`;
}

export function formatPosition(value: number): string {
	return Number.isFinite(value) ? value.toFixed(3) : "0.000";
}


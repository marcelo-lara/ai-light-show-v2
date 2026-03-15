function normalizeMs(value: number): number {
  return Math.max(0, Math.floor(value));
}

export function formatCurrentTimeMs(value: number): string {
  const totalMs = normalizeMs(value);
  const totalSeconds = Math.floor(totalMs / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = String(totalSeconds % 60).padStart(2, "0");
  const milliseconds = String(totalMs % 1000).padStart(3, "0");
  return `${minutes}:${seconds}.${milliseconds}`;
}

export function formatPosition(value: number): string {
	return `${value.toFixed(3)}`;
}

export function formatDurationMs(value: number): string {
  const total = Math.floor(normalizeMs(value) / 1000);
  const minutes = Math.floor(total / 60);
  const seconds = String(total % 60).padStart(2, "0");
  return `${minutes}:${seconds}`;
}

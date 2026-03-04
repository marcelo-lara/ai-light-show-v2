export function formatMs(value: number): string {
  const total = Math.max(0, Math.floor(value / 1000));
  const minutes = Math.floor(total / 60);
  const seconds = String(total % 60).padStart(2, "0");
  return `${minutes}:${seconds}`;
}

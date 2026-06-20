// Display-only formatting helpers. Pure functions, no side effects.

export function formatDuration(durationMs) {
  if (durationMs == null) return "未知";
  const totalSeconds = Math.floor(durationMs / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  const pad = (n) => String(n).padStart(2, "0");
  if (hours > 0) return `${hours}:${pad(minutes)}:${pad(seconds)}`;
  return `${minutes}:${pad(seconds)}`;
}

// Clamped 0–100 progress percentage for the now-playing bar.
export function progressPercent(positionMs, durationMs) {
  if (!durationMs) return 0;
  return Math.min(100, Math.max(0, (positionMs / durationMs) * 100));
}

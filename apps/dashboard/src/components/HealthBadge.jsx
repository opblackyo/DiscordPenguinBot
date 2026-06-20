// Small status pill mapping a status string to a colour + label.
// Read-only: it reflects state, it does not change it.

const STATUS_META = {
  online: { label: "在線", tone: "ok" },
  playing: { label: "播放中", tone: "ok" },
  paused: { label: "已暫停", tone: "warn" },
  idle: { label: "閒置", tone: "muted" },
  connected: { label: "已連線", tone: "ok" },
  degraded: { label: "異常", tone: "warn" },
  offline: { label: "離線", tone: "down" },
  disconnected: { label: "未連線", tone: "down" },
};

export default function HealthBadge({ status, label }) {
  const meta = STATUS_META[status] ?? { label: status, tone: "muted" };
  return (
    <span className={`badge badge--${meta.tone}`}>
      <span className="badge__dot" aria-hidden />
      {label ?? meta.label}
    </span>
  );
}

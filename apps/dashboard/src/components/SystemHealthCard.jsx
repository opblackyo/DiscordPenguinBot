// System health card — uptime and high-level runtime facts.
import { BoltIcon } from "./icons.jsx";

export default function SystemHealthCard({ health }) {
  const rows = [
    { label: "運行時間", value: health.uptime },
    { label: "作用中 players", value: String(health.activePlayers) },
    { label: "Lavalink 連線", value: health.lavalinkSecure ? "TLS" : "本機（非 TLS）" },
    { label: "部署位置", value: health.region },
  ];

  return (
    <section className="panel system-health" aria-label="系統健康">
      <header className="panel__header">
        <h2 className="panel__title">
          <BoltIcon width={18} height={18} />
          系統健康
        </h2>
      </header>
      <dl className="health-grid">
        {rows.map((row) => (
          <div key={row.label} className="health-grid__row">
            <dt>{row.label}</dt>
            <dd>{row.value}</dd>
          </div>
        ))}
      </dl>
      <div className="system-health__plugins">
        <span className="system-health__plugins-label">Lavalink plugins</span>
        <div className="system-health__plugins-list">
          {health.plugins.map((plugin) => (
            <span key={plugin} className="chip chip--plugin">{plugin}</span>
          ))}
        </div>
      </div>
    </section>
  );
}

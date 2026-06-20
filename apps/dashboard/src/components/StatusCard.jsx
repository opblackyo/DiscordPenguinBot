// One service status tile (Bot / API / Lavalink / Music).
import HealthBadge from "./HealthBadge.jsx";

const TONE_BY_STATUS = {
  online: "ok",
  playing: "ok",
  connected: "ok",
  paused: "warn",
  degraded: "warn",
  idle: "muted",
  offline: "down",
  disconnected: "down",
};

export default function StatusCard({ name, status, headline, detail, meta }) {
  const tone = TONE_BY_STATUS[status] ?? "muted";
  return (
    <article className={`status-card status-card--${tone}`}>
      <div className="status-card__top">
        <span className="status-card__name">{name}</span>
        <HealthBadge status={status} />
      </div>
      <p className="status-card__headline">{headline}</p>
      <p className="status-card__detail">{detail}</p>
      {meta ? <p className="status-card__meta">{meta}</p> : null}
    </article>
  );
}

// Source support card — which playback sources are configured.
import SourceBadge from "./SourceBadge.jsx";
import { MusicIcon } from "./icons.jsx";

export default function SourceCard({ sources }) {
  return (
    <section className="panel sources" aria-label="支援來源">
      <header className="panel__header">
        <h2 className="panel__title">
          <MusicIcon width={18} height={18} />
          支援來源
        </h2>
      </header>
      <ul className="sources__list">
        {sources.map((source) => (
          <li key={source.id} className="sources__item">
            <SourceBadge source={source.label} />
            <span className="sources__note">{source.note}</span>
            <span
              className={`sources__state ${
                source.enabled ? "sources__state--on" : "sources__state--off"
              }`}
            >
              {source.enabled ? "已啟用" : "停用"}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}

// Queue preview card — read-only list of upcoming tracks (FIFO order).
import SourceBadge from "./SourceBadge.jsx";
import { QueueIcon } from "./icons.jsx";
import { formatDuration } from "../lib/format.js";

export default function QueueCard({ items }) {
  return (
    <section className="panel queue" aria-label="播放佇列">
      <header className="panel__header">
        <h2 className="panel__title">
          <QueueIcon width={18} height={18} />
          下一首佇列
        </h2>
        <span className="chip chip--count">{items.length} 首</span>
      </header>

      {items.length === 0 ? (
        <div className="queue__empty">佇列目前是空的。</div>
      ) : (
        <ol className="queue__list">
          {items.map((item, index) => (
            <li key={item.id} className="queue__item">
              <span className="queue__index">{index + 1}</span>
              <div className="queue__meta">
                <p className="queue__title">{item.title}</p>
                <p className="queue__author">{item.author} · {item.requester}</p>
              </div>
              <div className="queue__right">
                <SourceBadge source={item.source} />
                <span className="queue__time">{formatDuration(item.durationMs)}</span>
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

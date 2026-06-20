// Now Playing card — read-only. Shows the current track, source, requester,
// voice context and a non-interactive progress bar. No playback controls.
import SourceBadge from "./SourceBadge.jsx";
import { PlayIcon, PauseIcon, IdleIcon, VoiceIcon } from "./icons.jsx";
import { formatDuration, progressPercent } from "../lib/format.js";

const STATE_META = {
  playing: { label: "播放中", Icon: PlayIcon, tone: "ok" },
  paused: { label: "已暫停", Icon: PauseIcon, tone: "warn" },
  idle: { label: "閒置", Icon: IdleIcon, tone: "muted" },
};

export default function NowPlayingCard({ track, voice }) {
  const state = STATE_META[track.state] ?? STATE_META.idle;
  const { Icon } = state;
  const isActive = track.state !== "idle";
  const percent = progressPercent(track.positionMs, track.durationMs);

  return (
    <section className="panel now-playing" aria-label="目前播放">
      <header className="panel__header">
        <h2 className="panel__title">目前播放</h2>
        <span className={`now-playing__state now-playing__state--${state.tone}`}>
          <Icon width={14} height={14} />
          {state.label}
        </span>
      </header>

      {isActive ? (
        <>
          <div className="now-playing__main">
            <div className="now-playing__art" aria-hidden>
              <Icon width={34} height={34} />
            </div>
            <div className="now-playing__info">
              <p className="now-playing__track">{track.title}</p>
              <p className="now-playing__author">{track.author}</p>
              <div className="now-playing__tags">
                <SourceBadge source={track.source} />
                <span className="chip chip--ghost">點歌者 · {track.requester}</span>
              </div>
            </div>
          </div>

          <div className="progress" role="presentation">
            <div className="progress__track">
              <div className="progress__fill" style={{ width: `${percent}%` }} />
            </div>
            <div className="progress__times">
              <span>{formatDuration(track.positionMs)}</span>
              <span>{formatDuration(track.durationMs)}</span>
            </div>
          </div>
        </>
      ) : (
        <div className="now-playing__empty">
          <IdleIcon width={28} height={28} />
          <p>目前沒有播放中的歌曲。</p>
        </div>
      )}

      <footer className="now-playing__voice">
        <VoiceIcon width={16} height={16} />
        {voice.state === "connected" ? (
          <span>
            {voice.guild} · <strong>{voice.channel}</strong> · {voice.listeners} 位聆聽者
          </span>
        ) : (
          <span>未連線到任何語音頻道</span>
        )}
      </footer>
    </section>
  );
}

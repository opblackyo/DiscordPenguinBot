// Phase 2B — Read-only Music Control Center, now API-backed.
// Fetches GET /api/music/status (same-origin, nginx-proxied to FastAPI) and
// renders live/degraded data. On API failure it falls back to clearly labeled
// demo data. This page still only DISPLAYS status — no playback controls.
import Layout from "./components/Layout.jsx";
import StatusCard from "./components/StatusCard.jsx";
import NowPlayingCard from "./components/NowPlayingCard.jsx";
import QueueCard from "./components/QueueCard.jsx";
import SourceCard from "./components/SourceCard.jsx";
import SystemHealthCard from "./components/SystemHealthCard.jsx";
import { buildMockView } from "./data/mockMusicStatus.js";
import { DataState, useMusicStatus } from "./lib/musicStatus.js";

const BANNERS = {
  [DataState.LOADING]: { tone: "loading", tag: "···", text: "正在連線 music status API…" },
  [DataState.LIVE]: { tone: "live", tag: "LIVE", text: "即時狀態 · 來自 bot 狀態快照" },
  [DataState.DEGRADED]: {
    tone: "degraded",
    tag: "降級",
    text: "部分服務降級或狀態快照較舊，以下為最後已知的安全狀態。",
  },
  [DataState.UNAVAILABLE]: {
    tone: "fallback",
    tag: "DEMO",
    text: "無法連線到 music status API，以下為示範資料（非即時）。",
  },
};

export default function App() {
  const { state, data } = useMusicStatus();

  // Live/degraded render the API envelope; loading/unavailable render the
  // clearly labeled mock so the Phase 2A layout never blanks out.
  const isLive = state === DataState.LIVE || state === DataState.DEGRADED;
  const view = isLive ? data : buildMockView();
  const banner = BANNERS[state];

  return (
    <Layout banner={banner}>
      <section className="status-grid" aria-label="服務狀態">
        {view.services.map((service) => (
          <StatusCard key={service.id} {...service} />
        ))}
      </section>

      <div className="main-grid">
        <div className="main-grid__primary">
          <NowPlayingCard track={view.nowPlaying} voice={view.voice} />
          <QueueCard items={view.queue} />
        </div>
        <div className="main-grid__secondary">
          <SourceCard sources={view.sources} />
          <SystemHealthCard health={view.health} />
        </div>
      </div>
    </Layout>
  );
}

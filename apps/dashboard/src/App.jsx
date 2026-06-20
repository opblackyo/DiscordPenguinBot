// Phase 2A — Read-only Music Control Center.
// This page only DISPLAYS status. It contains no playback controls and makes
// no API calls; all values come from the centralized mock in
// `src/data/mockMusicStatus.js`. Live wiring is deferred to a later phase.
import Layout from "./components/Layout.jsx";
import StatusCard from "./components/StatusCard.jsx";
import NowPlayingCard from "./components/NowPlayingCard.jsx";
import QueueCard from "./components/QueueCard.jsx";
import SourceCard from "./components/SourceCard.jsx";
import SystemHealthCard from "./components/SystemHealthCard.jsx";
import {
  MOCK_NOTICE,
  services,
  voice,
  nowPlaying,
  queue,
  sources,
  health,
} from "./data/mockMusicStatus.js";

export default function App() {
  return (
    <Layout notice={MOCK_NOTICE}>
      <section className="status-grid" aria-label="服務狀態">
        {services.map((service) => (
          <StatusCard key={service.id} {...service} />
        ))}
      </section>

      <div className="main-grid">
        <div className="main-grid__primary">
          <NowPlayingCard track={nowPlaying} voice={voice} />
          <QueueCard items={queue} />
        </div>
        <div className="main-grid__secondary">
          <SourceCard sources={sources} />
          <SystemHealthCard health={health} />
        </div>
      </div>
    </Layout>
  );
}

// App shell — branded header, status banner, content area and footer.
import { PenguinIcon } from "./icons.jsx";

// banner: { tone: "live" | "loading" | "degraded" | "fallback", tag, text }
export default function Layout({ banner, footerNote, children }) {
  return (
    <div className="shell">
      <header className="topbar">
        <div className="topbar__brand">
          <span className="topbar__logo" aria-hidden>
            <PenguinIcon />
          </span>
          <div className="topbar__titles">
            <span className="topbar__name">DiscordPenguinBot</span>
            <span className="topbar__sub">Music Control Center</span>
          </div>
        </div>
        <span className="topbar__phase">Phase 2B · Read-only</span>
      </header>

      {banner ? (
        <div className={`banner banner--${banner.tone}`} role="status">
          <span className="banner__tag">{banner.tag}</span>
          {banner.text}
        </div>
      ) : null}

      <main className="content">{children}</main>

      <footer className="footer">
        <span>私人 Discord 音樂控制中心</span>
        <span>{footerNote ?? "read-only status · GET /api/music/status"}</span>
      </footer>
    </div>
  );
}

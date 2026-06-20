// App shell — branded header, scrollable content area and footer.
import { PenguinIcon } from "./icons.jsx";

export default function Layout({ notice, children }) {
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
        <span className="topbar__phase">Phase 2A · Read-only</span>
      </header>

      {notice ? (
        <div className="notice" role="note">
          <span className="notice__tag">DEMO</span>
          {notice}
        </div>
      ) : null}

      <main className="content">{children}</main>

      <footer className="footer">
        <span>私人 Discord 音樂控制中心</span>
        <span>read-only status · 尚未連接 live music API</span>
      </footer>
    </div>
  );
}

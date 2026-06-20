// Inline SVG icons. Kept as local components so the dashboard adds no icon
// library dependency — only the existing React runtime is used. Each icon
// inherits `currentColor` so it picks up the surrounding text colour.

const base = {
  width: 18,
  height: 18,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 2,
  strokeLinecap: "round",
  strokeLinejoin: "round",
  "aria-hidden": true,
};

export function PlayIcon(props) {
  return (
    <svg {...base} {...props}>
      <polygon points="6 4 20 12 6 20 6 4" fill="currentColor" stroke="none" />
    </svg>
  );
}

export function PauseIcon(props) {
  return (
    <svg {...base} {...props}>
      <rect x="6" y="5" width="4" height="14" rx="1" fill="currentColor" stroke="none" />
      <rect x="14" y="5" width="4" height="14" rx="1" fill="currentColor" stroke="none" />
    </svg>
  );
}

export function IdleIcon(props) {
  return (
    <svg {...base} {...props}>
      <circle cx="12" cy="12" r="9" />
      <line x1="12" y1="7" x2="12" y2="12" />
      <line x1="12" y1="12" x2="15" y2="14" />
    </svg>
  );
}

export function MusicIcon(props) {
  return (
    <svg {...base} {...props}>
      <path d="M9 18V5l12-2v13" />
      <circle cx="6" cy="18" r="3" />
      <circle cx="18" cy="16" r="3" />
    </svg>
  );
}

export function QueueIcon(props) {
  return (
    <svg {...base} {...props}>
      <line x1="3" y1="6" x2="15" y2="6" />
      <line x1="3" y1="12" x2="15" y2="12" />
      <line x1="3" y1="18" x2="11" y2="18" />
      <path d="M18 9v8" />
      <circle cx="20" cy="17" r="2" />
    </svg>
  );
}

export function BoltIcon(props) {
  return (
    <svg {...base} {...props}>
      <path d="M13 2 4 14h7l-1 8 9-12h-7l1-8z" fill="currentColor" stroke="none" />
    </svg>
  );
}

export function VoiceIcon(props) {
  return (
    <svg {...base} {...props}>
      <path d="M11 5 6 9H2v6h4l5 4V5z" />
      <path d="M15.5 8.5a5 5 0 0 1 0 7" />
      <path d="M18.5 6a8 8 0 0 1 0 12" />
    </svg>
  );
}

export function PenguinIcon(props) {
  // Compact penguin glyph for the brand mark.
  return (
    <svg viewBox="0 0 24 24" width={22} height={22} aria-hidden {...props}>
      <path
        d="M12 2c-3.3 0-5.5 2.6-5.5 6.2 0 1.6.2 2.6.2 4.1C6.7 16 5 17.4 5 19.2 5 21 6.6 22 9 22h6c2.4 0 4-1 4-2.8 0-1.8-1.7-3.2-1.7-6.9 0-1.5.2-2.5.2-4.1C17.5 4.6 15.3 2 12 2z"
        fill="currentColor"
      />
      <ellipse cx="12" cy="14" rx="3" ry="4.2" fill="#0b0e16" />
      <circle cx="9.6" cy="8.2" r="1.1" fill="#0b0e16" />
      <circle cx="14.4" cy="8.2" r="1.1" fill="#0b0e16" />
      <path d="M12 9.2l1.6 1.6h-3.2z" fill="#f5a623" />
    </svg>
  );
}

export function YouTubeIcon(props) {
  return (
    <svg viewBox="0 0 24 24" width={16} height={16} aria-hidden {...props}>
      <path
        d="M22.5 7.2a2.8 2.8 0 0 0-2-2C18.8 4.7 12 4.7 12 4.7s-6.8 0-8.5.5a2.8 2.8 0 0 0-2 2A29 29 0 0 0 1 12a29 29 0 0 0 .5 4.8 2.8 2.8 0 0 0 2 2c1.7.5 8.5.5 8.5.5s6.8 0 8.5-.5a2.8 2.8 0 0 0 2-2A29 29 0 0 0 23 12a29 29 0 0 0-.5-4.8z"
        fill="currentColor"
      />
      <path d="M9.8 15.3V8.7l5.7 3.3z" fill="#0b0e16" />
    </svg>
  );
}

export function BilibiliIcon(props) {
  return (
    <svg viewBox="0 0 24 24" width={16} height={16} aria-hidden {...props}>
      <path
        d="M7.2 2.6 9.6 5h4.8l2.4-2.4a1 1 0 0 1 1.4 1.4L17.4 5H19a3 3 0 0 1 3 3v9a3 3 0 0 1-3 3H5a3 3 0 0 1-3-3V8a3 3 0 0 1 3-3h1.6L5.8 4a1 1 0 0 1 1.4-1.4z"
        fill="currentColor"
      />
      <rect x="7.5" y="10" width="2" height="4" rx="1" fill="#0b0e16" />
      <rect x="14.5" y="10" width="2" height="4" rx="1" fill="#0b0e16" />
    </svg>
  );
}

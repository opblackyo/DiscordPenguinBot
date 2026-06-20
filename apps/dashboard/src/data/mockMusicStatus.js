// =============================================================================
// Phase 2A — MOCK / DEMO DATA ONLY
// -----------------------------------------------------------------------------
// This file is the SINGLE source of demo data for the read-only Music Control
// Center. Nothing here is live: there is no music status API yet. When Phase 2B
// wires a real backend, replace the exports below with a data fetch and delete
// this notice. Everything in `src/components` consumes these shapes, so keeping
// the mock isolated here keeps the swap to live data trivial.
// =============================================================================

export const MOCK_NOTICE =
  "Phase 2A read-only UI shell — values below are demo data, not yet wired to a live music API.";

// Service status pills shown across the top of the dashboard.
// status ∈ "online" | "playing" | "paused" | "idle" | "degraded" | "offline"
export const services = [
  {
    id: "bot",
    name: "Discord Bot",
    status: "online",
    headline: "已連線",
    detail: "以 PenguinBot#4821 身分上線",
    meta: "Gateway 延遲 42ms",
  },
  {
    id: "api",
    name: "API",
    status: "online",
    headline: "正常",
    detail: "FastAPI /health 回應 ok",
    meta: "回應時間 11ms",
  },
  {
    id: "lavalink",
    name: "Lavalink",
    status: "online",
    headline: "可連線",
    detail: "私人 v4 node 已就緒",
    meta: "youtube-source + lavabili",
  },
  {
    id: "music",
    name: "Music",
    status: "playing",
    headline: "播放中",
    detail: "正在 音樂頻道 串流",
    meta: "1 個作用中的 player",
  },
];

// Voice / connection state for the now-playing context strip.
export const voice = {
  state: "connected", // "connected" | "idle" | "disconnected"
  guild: "企鵝的私人小窩",
  channel: "音樂頻道",
  listeners: 3,
};

// The currently playing track.
// state ∈ "playing" | "paused" | "idle"
export const nowPlaying = {
  state: "playing",
  title: "夜に駆ける",
  author: "YOASOBI",
  source: "YouTube", // matches the bot's source_label() output: YouTube | Bilibili
  requester: "blackyo",
  durationMs: 261000,
  positionMs: 96000,
  uri: "https://www.youtube.com/watch?v=demo",
};

// Upcoming queue preview (FIFO order). Mirrors the per-guild queue domain model.
export const queue = [
  {
    id: "q1",
    title: "群青",
    author: "YOASOBI",
    source: "YouTube",
    requester: "blackyo",
    durationMs: 280000,
  },
  {
    id: "q2",
    title: "好きだ",
    author: "Yorushika",
    source: "YouTube",
    requester: "penguin_fan",
    durationMs: 246000,
  },
  {
    id: "q3",
    title: "極樂淨土",
    author: "GARNiDELiA",
    source: "Bilibili",
    requester: "mochi",
    durationMs: 257000,
  },
  {
    id: "q4",
    title: "千本桜",
    author: "黒うさP",
    source: "Bilibili",
    requester: "blackyo",
    durationMs: 244000,
  },
];

// Supported playback sources, mirroring the configured Lavalink plugins.
export const sources = [
  {
    id: "youtube",
    label: "YouTube",
    enabled: true,
    note: "官方 youtube-source plugin",
  },
  {
    id: "bilibili",
    label: "Bilibili",
    enabled: true,
    note: "lavabili-plugin · JitPack 3bac0c10cc",
  },
];

// High-level system health summary.
export const health = {
  uptime: "3 天 7 小時 12 分",
  activePlayers: 1,
  lavalinkSecure: false,
  plugins: ["youtube-source", "lavabili-plugin"],
  region: "本機私人部署",
};

# DiscordPenguinBot

DiscordPenguinBot 是一個模組化的私人 Discord 控制中心。Phase 1F 在既有音樂 MVP 上補齊播放穩定性、基本控制與 voice cleanup。

## Current status

- Discord bot：環境設定讀取、結構化 logging 與 `/ping` slash command。
- API：FastAPI health endpoint。
- Dashboard：React/Vite「Music Control Center」read-only 狀態頁（Phase 2A）。深色 Discord 風格版面，顯示服務狀態、目前播放、佇列預覽、來源支援與系統健康。**目前使用集中於 `apps/dashboard/src/data/mockMusicStatus.js` 的 demo data，尚未連接 live music API；本階段不含任何播放控制。**
- Lavalink：Docker Compose 的私人 v4 node service，使用官方 `youtube-source` plugin 與固定 JitPack commit 的 `lavabili-plugin` 載入 YouTube 和 Bilibili 影片；bot 在 Discord ready 後以 Wavelink 背景連線，離線時不會阻擋 `/ping`。
- Music status：`/music-status` 只會回報 configured、reachable、host、port、secure 與安全的 error summary，絕不輸出 password。
- Queue domain：`TrackRequest`、FIFO `GuildQueue` 與 `GuildQueueStore` 保持為純記憶體 domain model；Wavelink 的 runtime track 只存在 playback adapter 層。
- Music MVP：`/play query` 會載入支援的 YouTube 或 Bilibili 單曲網址、加入呼叫者所在語音頻道並在閒置時開始播放；`/queue`、`/nowplaying`、`/skip`、`/stop`、`/pause`、`/resume` 會操作各 guild 獨立的 queue。播放回覆使用繁體中文 Embed，顯示歌曲、作者、長度、來源、點歌者與可用的來源連結。
- Playback stability：Lavalink track exception / stuck event 會安全嘗試下一首；bot 被移出語音時會清理該 guild queue；頻道只剩 bot 時會在短暫延遲後離開並清理 queue。`/skip` 與 `/stop` 允許管理員、Manage Guild、點歌者或和 bot 同語音頻道的使用者操作。
- Tests：smoke test 會確認所有 Phase 1C 指令已註冊；playback tests 驗證 FIFO、per-guild isolation、失敗跳過與 stop 清理。

刻意未實作：loop/shuffle、playlist、lyrics、queue persistence、Dashboard 控制與 AI。這些功能不屬於 Phase 1F。

### Phase 2A — Dashboard read-only music status UI

Phase 2A 只做 Dashboard 的視覺層，把首頁做成「私人 Discord 音樂控制中心」的 read-only 樣貌：

- 視覺：深色主題、Discord/gaming dashboard 風格，使用既有的 React 19 + Vite 6 與純 CSS（未新增 UI 或 icon library，圖示為內嵌 SVG）。
- 區塊：Header、服務狀態卡（Bot / API / Lavalink / Music）、Now Playing、Queue 預覽、來源支援（YouTube / Bilibili）與系統健康。
- 元件：`Layout`、`StatusCard`、`NowPlayingCard`、`QueueCard`、`SourceCard`、`SourceBadge`、`HealthBadge`、`SystemHealthCard`。

**限制與現況：**

- 這是 read-only UI shell。畫面上的資料目前**全部來自 mock**，集中於單一檔案 [`apps/dashboard/src/data/mockMusicStatus.js`](apps/dashboard/src/data/mockMusicStatus.js)，**尚未連接 live music status API**。
- 本階段**沒有任何播放控制**（無 play / skip / stop / pause / resume 按鈕），也沒有新增 Dashboard 操作 API、登入系統、AI 或 database persistence。
- 未改動 bot 播放流程、Lavalink plugin 版本或 API `/health`。
- 接上真實資料是後續階段的工作：屆時只需把 `mockMusicStatus.js` 的 export 換成資料抓取即可，元件的資料形狀已對齊 bot 的 queue / source 概念。

## Prerequisites

- Docker Desktop with Docker Compose v2+
- 或 Python 3.11+（本機測試）與 Node.js 22+（只在本機開發 Dashboard 時需要）

## Configure

1. Copy the safe template:

   ```powershell
   Copy-Item .env.example .env
   ```

2. Set at least `DISCORD_TOKEN` before running the bot. Set `DISCORD_CLIENT_ID` and, for immediate development-guild command sync, `DISCORD_GUILD_ID`.
3. Set a unique `LAVALINK_PASSWORD` before starting the Lavalink container. Do not expose port 2333 beyond the host.

`DISCORD_TOKEN`, AI keys, Lavalink passwords, Dashboard secrets and database files are intentionally ignored by Git.

## Run and verify

Validate Compose without starting any services:

```powershell
docker compose config
```

Run the complete skeleton after configuration:

```powershell
docker compose up --build
```

The API is available at `http://localhost:8000/health`; the Dashboard is available at `http://localhost:3000`. The bot registers `/ping`, `/music-status`, `/play`, `/queue`, `/nowplaying`, `/skip`, `/stop`, `/pause`, and `/resume` when it connects to Discord. A configured `DISCORD_GUILD_ID` scopes sync to that guild for development; otherwise the commands are global.

`/music-status` is available after the bot connects to Discord. It reports whether the configured private Lavalink node is reachable without exposing `LAVALINK_PASSWORD`. A Lavalink outage is reported as a safe status error and does not prevent the bot from serving `/ping`.

For playback, join a voice channel and run `/play query:<song, YouTube URL, or Bilibili video URL>`. Only one resolved track is accepted per command; playlist results are intentionally rejected in this phase. YouTube links containing a direct video ID are normalised to that single video, rather than accidentally loading an attached mix or playlist. The Bilibili source uses the fixed `lavabili-plugin` JitPack commit `3bac0c10cc`; no account cookie is configured. When a track ends, the bot starts the next item in that server's FIFO queue. `/stop` clears the in-memory queue and disconnects the bot from voice.

For local Python smoke tests:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\python -m apps.bot.penguin_bot.main --check-config
.venv\Scripts\python -m pytest
```

## Project layout

```text
apps/
  bot/penguin_bot/       Discord bot and configuration
  api/penguin_api/       FastAPI service
  dashboard/             React/Vite Music Control Center (read-only UI)
services/lavalink/       Lavalink service notes
tests/                   Phase 0 smoke tests
docker-compose.yml       Local service orchestration
```

## Repository workflow

- `main` 是穩定分支。
- 新功能請從 `main` 建立短期分支，例如 `feat/music-mvp`。
- 使用 Conventional Commits，例如 `feat(bot): add slash-command skeleton`。
- 完成後以 Draft Pull Request 合併回 `main`。

## Planned milestones

1. Lavalink music MVP
2. Authenticated dashboard MVP
3. Permission and database layer
4. Provider-neutral AI adapter

## License

MIT. See [LICENSE](LICENSE).

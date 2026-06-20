# DiscordPenguinBot

DiscordPenguinBot 是一個模組化的私人 Discord 控制中心。Phase 1F 在既有音樂 MVP 上補齊播放穩定性、基本控制與 voice cleanup。

## Current status

- Discord bot：環境設定讀取、結構化 logging 與 `/ping` slash command。
- API：FastAPI health endpoint。
- Dashboard：React/Vite「Music Control Center」read-only 狀態頁。深色 Discord 風格版面，顯示服務狀態、目前播放、佇列預覽、來源支援與系統健康。**Phase 2B 起已接 live：透過同源 `/api/music/status`（nginx 反向代理到 API）讀取 bot 寫出的狀態快照；API 不可達時自動降級為明確標示的示範資料。本階段仍不含任何播放控制。**
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

### Phase 2B — Read-only music status API

Phase 2B 讓 Dashboard 讀真實狀態，但仍維持 **read-only**（不新增任何控制 / 操作 endpoint）。資料流：

```text
Bot runtime state
  → sanitized snapshot（bot 寫，single primary-guild context）
  → shared runtime volume（./tmp/music-status，runtime-only、git-ignored、不含 secret）
  → FastAPI GET /music/status（只讀，missing/stale/invalid 都回 200 degraded envelope）
  → Dashboard fetch /api/music/status（nginx 同源反向代理到 api:8000）
  → Phase 2A 版面渲染 live / degraded / fallback
```

要點與邊界：

- **Bot 端**：[`status_snapshot.py`](apps/bot/penguin_bot/music/status_snapshot.py) 在 ready / 換歌 / pause-resume / skip-stop / voice cleanup / 例外恢復 與每 5 秒定期，best-effort 原子寫出 sanitized 快照（temp + `os.replace`，失敗不影響播放）。primary-guild 選取在 bot 端完成（`DISCORD_GUILD_ID` → 最小 active → 最小 queued → idle）；`voice / nowPlaying / queue` 為單一 primary guild，`health.activePlayers` 為全域。source label 重用既有 `presentation.source_label()`。
- **API 端**：[`music_status.py`](apps/api/penguin_api/music_status.py) 純讀快照、逐欄位 allow-list 重建（未知欄位不會外洩），固定回傳 `services`（bot/api/lavalink/music 各一）與 `sources`（含 youtube/bilibili）；`api` service 一律 online。API **不取得 `LAVALINK_*` 憑證、不直連 Lavalink**；Lavalink 狀態只來自快照。
- **Dashboard 端**：on load fetch `/api/music/status`，狀態 `loading / live / degraded / api-unavailable`；API 不可達（含代理回傳 HTML 而非 JSON）時退回明確標示的 mock fallback，版面不白屏。dev 以 Vite proxy 對應同一 `/api` 路徑（dev-only 便利，docker 由 nginx 提供）。
- 環境變數：`MUSIC_STATUS_SNAPSHOT_PATH`（bot 與 api 共用）、`MUSIC_STATUS_STALE_AFTER_MS`（api，預設 15000）。快照檔在 `./tmp` 之下，永不提交。

**本階段仍未做**：play / skip / stop / pause / resume 控制、mutation endpoint、登入 / 權限、WebSocket、database persistence、新增 bot command；未改 Lavalink plugin 版本、既有播放流程或 API `/health`。

#### 本機開發與營運（local dev / ops）

完整 stack 直接 `docker compose up --build` 即可；以下是只驗證 read-only 狀態鏈、不啟動 bot（避免用真 token 連 Discord）的做法：

1. 只啟動 API 與 Dashboard：

   ```powershell
   docker compose up -d --build api dashboard
   ```

2. 注入一份測試快照到共享 runtime 目錄（API 以唯讀掛載讀取）。`./tmp/music-status` 是 **runtime-only、git-ignored、可刪可重生、不含 secret**；缺少時 bot 端 writer 會自動建立：

   ```powershell
   # 寫入 ./tmp/music-status/status.json 後即可被 api 讀到
   # （實際執行時由 bot 自動寫出；本機驗證可用 status_snapshot 的 builders 產生一份）
   ```

3. 驗證端點：

   ```powershell
   curl http://localhost:8000/health
   curl http://localhost:8000/music/status
   curl http://localhost:3000/api/music/status   # 經 dashboard nginx 同源代理，必為 JSON 而非 index.html
   ```

4. 收尾（避免殘留容器占用 port 8000 / 3000）：

   ```powershell
   docker compose down
   ```

純前端開發（`npm run dev`）時，Vite dev server 會把 `/api` 代理到 API，等同 docker 內 nginx 的同源行為；預設目標 `http://127.0.0.1:8000`，可用 **dev-only** 環境變數 `VITE_DEV_API_TARGET` 覆寫（僅影響本機 dev，docker/production 路徑一律走 nginx 的 `/api`）。

快照逾時門檻由 `MUSIC_STATUS_STALE_AFTER_MS`（API，預設 15000ms）決定；超過即回 `degraded` 並帶 `SNAPSHOT_STALE`。bot 每 5 秒定期改寫快照，因此正常運行時 `snapshotWrittenAt` 會持續更新；bot 停止後快照轉為 stale，API 仍回 200 degraded，不會讓 Dashboard 白屏。

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

The API is available at `http://localhost:8000/health` and `http://localhost:8000/music/status`; the Dashboard is available at `http://localhost:3000` and proxies the API at `http://localhost:3000/api/music/status`. The bot registers `/ping`, `/music-status`, `/play`, `/queue`, `/nowplaying`, `/skip`, `/stop`, `/pause`, and `/resume` when it connects to Discord. A configured `DISCORD_GUILD_ID` scopes sync to that guild for development; otherwise the commands are global.

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

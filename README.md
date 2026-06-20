# DiscordPenguinBot

DiscordPenguinBot 是一個模組化的私人 Discord 控制中心。Phase 1E 在既有音樂 MVP 上加入固定版本的私人 Bilibili Lavalink source。

## Current status

- Discord bot：環境設定讀取、結構化 logging 與 `/ping` slash command。
- API：FastAPI health endpoint。
- Dashboard：React/Vite status-page skeleton。
- Lavalink：Docker Compose 的私人 v4 node service，使用官方 `youtube-source` plugin 與固定 JitPack commit 的 `lavabili-plugin` 載入 YouTube 和 Bilibili 影片；bot 在 Discord ready 後以 Wavelink 背景連線，離線時不會阻擋 `/ping`。
- Music status：`/music-status` 只會回報 configured、reachable、host、port、secure 與安全的 error summary，絕不輸出 password。
- Queue domain：`TrackRequest`、FIFO `GuildQueue` 與 `GuildQueueStore` 保持為純記憶體 domain model；Wavelink 的 runtime track 只存在 playback adapter 層。
- Music MVP：`/play query` 會載入支援的 YouTube 或 Bilibili 單曲網址、加入呼叫者所在語音頻道並在閒置時開始播放；`/queue`、`/nowplaying`、`/skip`、`/stop` 會操作各 guild 獨立的 queue。播放回覆使用繁體中文 Embed，顯示歌曲、作者、長度、點歌者與可用的來源連結。Lavalink 未連線時，`/play` 會安全拒絕而不影響 `/ping`。
- Tests：smoke test 會確認所有 Phase 1C 指令已註冊；playback tests 驗證 FIFO、per-guild isolation、失敗跳過與 stop 清理。

刻意未實作：pause/resume、loop/shuffle、playlist、lyrics、queue persistence、Dashboard 控制與 AI。這些功能不屬於 Phase 1E。

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

The API is available at `http://localhost:8000/health`; the Dashboard is available at `http://localhost:3000`. The bot registers `/ping`, `/music-status`, `/play`, `/queue`, `/nowplaying`, `/skip`, and `/stop` when it connects to Discord. A configured `DISCORD_GUILD_ID` scopes sync to that guild for development; otherwise the commands are global.

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
  dashboard/             React/Vite UI skeleton
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

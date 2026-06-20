# DiscordPenguinBot

DiscordPenguinBot 是一個模組化的私人 Discord 控制中心。Phase 0 已建立可啟動的 bot、FastAPI API、React Dashboard 和私人 Lavalink v4 service 骨架；音樂播放、AI 與控制功能會在後續階段加入。

## Phase 0 status

- Discord bot：環境設定讀取、結構化 logging 與 `/ping` slash command。
- API：FastAPI health endpoint。
- Dashboard：React/Vite status-page skeleton。
- Lavalink：Docker Compose 的私人 v4 node service；尚未由 bot 使用。
- Tests：smoke test 會匯入 bot 與 API，並確認 `/ping` 已註冊。

未實作：音樂指令、音源搜尋、AI、資料庫寫入、Dashboard authentication 與控制按鈕。這些功能不屬於 Phase 0。

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

The API is available at `http://localhost:8000/health`; the Dashboard is available at `http://localhost:3000`. The bot registers `/ping` when it connects to Discord. A configured `DISCORD_GUILD_ID` scopes sync to that guild for development; otherwise the command is global.

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

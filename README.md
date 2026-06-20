# DiscordPenguinBot

DiscordPenguinBot 是一個正在建立中的模組化私人 Discord 控制中心：音樂播放會使用 Lavalink，並預留 AI、Dashboard、監控與權限模組。

## Repository workflow

- `main` 是穩定分支。
- 新功能請從 `main` 建立短期分支，例如 `feat/music-mvp`。
- 使用 Conventional Commits，例如 `feat(bot): add slash-command skeleton`。
- 完成後以 Draft Pull Request 合併回 `main`。

## Security

**絕不可提交** Discord token、Lavalink password、AI API key、Dashboard secret、私鑰或實際資料庫檔案。

複製 `.env.example` 為 `.env` 後，僅在本機或受保護的部署環境填入真實設定：

```powershell
Copy-Item .env.example .env
```

`.env` 和常見憑證、日誌、快取與執行資料已列入 `.gitignore`。推送前仍應檢查 `git status` 與 staged diff，避免意外洩漏資訊。

## Planned milestones

1. Modular bot project skeleton
2. Lavalink music MVP
3. Authenticated dashboard MVP
4. Provider-neutral AI adapter

## License

MIT. See [LICENSE](LICENSE).

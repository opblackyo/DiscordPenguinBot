# Phase 2B Contract — INPUT ONLY / NOT A LOCKED SPEC

> ⚠️ **狀態：`INPUT_ONLY`。這份文件不是 Phase 2B Locked Spec、不是授權實作、不是 API 最終契約。**
>
> 它只是 **Phase 2A → Phase 2B 的交接參考**：把目前 Dashboard 已經在消費的 mock data 形狀、source label 對齊規則、nullable / degraded 情境整理進 repo，讓之後撰寫 Phase 2B Locked Spec、API 實作與前端接線時有同一份可對照的底稿。
>
> **這份文件不授權任何下列動作：** 新增 / 修改 API、修改 `apps/api`、`apps/bot`、`apps/dashboard`、修改 mock data、開工 Phase 2B。實作必須等正式的 **Phase 2B Locked Spec** 與明確授權。

---

## 1. 這份文件「是」與「不是」什麼

| 是 | 不是 |
| --- | --- |
| 目前 Dashboard mock data 的輸入參考 | Phase 2B Locked Spec |
| source label 對齊規則的記錄 | API 最終契約 |
| nullable / degraded case 的清單 | 授權實作的依據 |
| 給 Phase 2B spec writer 的注意事項 | 任何 endpoint 行為保證 |

---

## 2. 現況基準

- `Music MVP+ = STABLE_PRIVATE_MUSIC_BOT_BASELINE`
- `Dashboard 2A = READ_ONLY_UI_BASELINE_LOCKED`
- 目前 Dashboard 的所有畫面資料皆為 **mock**，集中於單一檔案 [`apps/dashboard/src/data/mockMusicStatus.js`](../apps/dashboard/src/data/mockMusicStatus.js)。
- 尚未存在任何 live music status API。

Phase 2B 的目標（待 Locked Spec 確認）是讓 Dashboard **讀**真實狀態；前端只需把該 mock 檔的 export 換成一次 API fetch，元件資料形狀已預先對齊。

---

## 3. 目前 Dashboard 消費的資料形狀

以下為 Dashboard 元件目前實際讀取的欄位。**這是「前端已預期的輸入」，供 spec 對齊用，不代表 API 必須一字不差地回傳。** 命名 / 巢狀 / 分組由 Locked Spec 決定。

### 3.1 services[]（服務狀態卡：Bot / API / Lavalink / Music）

| 欄位 | 型別 | 說明 |
| --- | --- | --- |
| `id` | string | `bot` \| `api` \| `lavalink` \| `music` |
| `name` | string | 顯示名稱 |
| `status` | enum | `online` \| `playing` \| `paused` \| `idle` \| `degraded` \| `offline` |
| `headline` | string | 短狀態詞（例：`播放中`） |
| `detail` | string | 一行細節 |
| `meta` | string \| null | 次要資訊（延遲、plugin 等），可省略 |

### 3.2 voice（語音 / 連線狀態）

| 欄位 | 型別 | 說明 |
| --- | --- | --- |
| `state` | enum | `connected` \| `idle` \| `disconnected` |
| `guild` | string | 伺服器名稱 |
| `channel` | string | 語音頻道名稱 |
| `listeners` | number | 聆聽人數 |

### 3.3 nowPlaying（目前播放）

| 欄位 | 型別 | 說明 |
| --- | --- | --- |
| `state` | enum | `playing` \| `paused` \| `idle` |
| `title` | string | 歌曲標題 |
| `author` | string | 作者 / 上傳者 |
| `source` | enum | `YouTube` \| `Bilibili`（見 §4） |
| `requester` | string | 點歌者顯示名稱 |
| `durationMs` | number \| null | 總長度（毫秒），未知為 null |
| `positionMs` | number \| null | 目前進度（毫秒），未知為 null |
| `uri` | string \| null | 來源連結，顯示用 |

### 3.4 queue[]（下一首佇列，FIFO 順序）

| 欄位 | 型別 | 說明 |
| --- | --- | --- |
| `id` | string | 穩定 key（前端 list key 用） |
| `title` | string | 歌曲標題 |
| `author` | string | 作者 |
| `source` | enum | `YouTube` \| `Bilibili`（見 §4） |
| `requester` | string | 點歌者 |
| `durationMs` | number \| null | 長度（毫秒），未知為 null |

### 3.5 sources[]（支援來源）

| 欄位 | 型別 | 說明 |
| --- | --- | --- |
| `id` | string | `youtube` \| `bilibili` |
| `label` | string | `YouTube` \| `Bilibili` |
| `enabled` | boolean | 是否啟用 |
| `note` | string | plugin / 來源註記 |

### 3.6 health（系統健康）

| 欄位 | 型別 | 說明 |
| --- | --- | --- |
| `uptime` | string | 人類可讀運行時間 |
| `activePlayers` | number | 作用中 player 數 |
| `lavalinkSecure` | boolean | Lavalink 連線是否 TLS |
| `plugins` | string[] | 載入的 Lavalink plugin |
| `region` | string | 部署位置描述 |

---

## 4. source label 對齊規則（重要）

`source` 的值必須與 **bot 既有邏輯** 一致，前後端不要各自定義。

bot 端唯一的真實來源是 [`apps/bot/penguin_bot/music/presentation.py`](../apps/bot/penguin_bot/music/presentation.py) 的 `source_label()`，它依 host 判斷後**只輸出三種值**：

- `YouTube` — host 屬於 `youtube.com` / `m.youtube.com` / `music.youtube.com` / `youtu.be`
- `Bilibili` — host 為 `bilibili.com` / `*.bilibili.com` / `b23.tv`
- `Unknown` — 其他

**Phase 2B 注意事項：**
- API 回傳的 `source` 應沿用同一組標籤值（含 `Unknown`）。
- 目前 Dashboard 的 `SourceBadge` 對未知值已有 neutral fallback，但 `Unknown` 尚未出現在 mock；Locked Spec 應決定 `Unknown` 是否會出現以及前端如何呈現。
- 不要在前端重新實作 host→label 的判斷邏輯；以 API（= bot 邏輯）為準。

---

## 5. Nullable / degraded / empty 情境（前端已預期）

Locked Spec 應明確定義以下情境的回應形狀，前端的 loading / error / empty state 才有依據：

- **nowPlaying = idle**：沒有播放中歌曲。前端顯示「目前沒有播放中的歌曲」空態，不需要 `title` / `durationMs` / `positionMs`。
- **`durationMs` / `positionMs` 未知**：前端容許 null（進度條與時間以 `未知` / 0% 呈現）。
- **queue 為空**：前端顯示「佇列目前是空的」。
- **voice 未連線**（`disconnected` / `idle`）：前端顯示「未連線到任何語音頻道」。
- **Lavalink 離線 / 不可達**：對應 service `status = degraded | offline`。需定義此時 `nowPlaying` / `queue` 是否仍回傳、或回降級結構。
- **整體 API 不可達**：純前端議題，但 Locked Spec 應明確「部分資料缺失」與「整包失敗」的差別，讓前端能分辨 partial vs error。

---

## 6. 給 Phase 2B Locked Spec writer 的邊界提醒

Phase 2B 必須維持 **read-only**。下列項目**不屬於** Phase 2B，spec 不應納入：

- ❌ 播放控制：play / skip / stop / pause / resume
- ❌ 任何會改變 bot / player 狀態的 endpoint（只允許 `GET`，不允許 mutation）
- ❌ 登入 / 權限系統
- ❌ WebSocket / 即時推播（Phase 2B 為一次性讀取；即時更新另議）
- ❌ database persistence
- ❌ 新增 bot command
- ❌ 修改 Lavalink plugin 版本
- ❌ 修改既有 bot 播放流程

最容易踩的雷：**把 read-only status API 不小心做成半個控制後端。** 任何「順便也能操作」的設計都應在 spec 階段被擋下。

---

## 7. 後續順序（參考，非授權）

1. 依本 input doc 產出 **Phase 2B Locked Spec**。
2. 由 Codex / GPT 審查 API contract 是否破壞 bot / dashboard 邊界。
3. 通過後，才授權實作 `GET /music/status`。
4. Dashboard 從 mock 切到 API fetch，保留 mock fallback / loading / error state。
5. final review / merge gate 由 repo owner 把關（PR 一律走 Draft PR → main，作者不自行 merge）。

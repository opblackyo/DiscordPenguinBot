# Lavalink service

The project runs a private Lavalink v4 service in `docker-compose.yml`, using the official `ghcr.io/lavalink-devs/lavalink:4-alpine` image. The service is internal to Docker Compose and its port is bound only to `127.0.0.1` for local diagnostics.

Set `LAVALINK_PASSWORD` in `.env`; Compose passes it to Lavalink as `LAVALINK_SERVER_PASSWORD`, the documented environment-variable form of `lavalink.server.password`.

`application.yml` installs the official `youtube-source` plugin (`1.18.1`) and disables Lavalink's deprecated built-in YouTube source. This is required for current YouTube track loading. It also installs `hoyiliang/lavabili-plugin` from the fixed JitPack commit `3bac0c10cc` to load direct Bilibili videos. Both plugins are downloaded by Lavalink at container start; no YouTube/Bilibili account, cookie, OAuth token, poToken, or public Lavalink node is configured or committed.

The configuration supports direct YouTube and Bilibili videos. Searches and playlists remain intentionally outside Bilibili support for this MVP.

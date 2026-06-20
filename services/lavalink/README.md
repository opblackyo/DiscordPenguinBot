# Lavalink service placeholder

Phase 0 declares a private Lavalink v4 service in `docker-compose.yml`, using the official `ghcr.io/lavalink-devs/lavalink:4-alpine` image. The service is internal to Docker Compose and its port is bound only to `127.0.0.1` for local diagnostics.

Set `LAVALINK_PASSWORD` in `.env`; Compose passes it to Lavalink as `LAVALINK_SERVER_PASSWORD`, the documented environment-variable form of `lavalink.server.password`.

No bot music client, source plugins, public nodes, or playback configuration are included until Phase 1.

"""CLI entrypoint for the Discord bot."""

from __future__ import annotations

import argparse
import logging

from .bot import create_bot
from .config import ConfigurationError, Settings


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run DiscordPenguinBot.")
    parser.add_argument(
        "--check-config",
        action="store_true",
        help="Read configuration and log only safe status facts without connecting to Discord.",
    )
    args = parser.parse_args(argv)

    configure_logging()
    logger = logging.getLogger(__name__)

    try:
        settings = Settings.from_environment()
        logger.info("Configuration loaded: %s", settings.safe_status())
        if args.check_config:
            bot = create_bot(settings)
            logger.info(
                "Bot initialized without connecting to Discord. Registered commands: %s",
                [command.name for command in bot.tree.get_commands()],
            )
            return 0

        bot = create_bot(settings)
        bot.run(settings.require_discord_token(), log_handler=None)
        return 0
    except ConfigurationError as error:
        logger.error("Configuration error: %s", error)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

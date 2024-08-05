import asyncio
from bot import bot
from config.common import bot_cfg


def main() -> None:
    bot_instance = bot.get_bot(bot_cfg.token)
    dispatcher = bot.prepare_bot(bot_instance)
    asyncio.run(dispatcher.run_polling(bot_instance))
    int()

if __name__ == "__main__":
    main()

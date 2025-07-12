from aiogram.types import BotCommand, BotCommandScopeChat

from config.loader import bot_instance


def get_default_commands() -> list[BotCommand]:
    commands = [
        BotCommand(command="/start", description="(re)Start the bot"),
        BotCommand(command="/help", description="Get list of commands and their definitions"),
        BotCommand(command="/me", description="Info about yourself"),
        BotCommand(command="/contact", description="Contact the admins"),
        BotCommand(command="/config", description="Get configs of peers"),
        BotCommand(command="/unblock", description="Unblock/update the connection"),
        BotCommand(command="/change_peer_name", description="Change peer name (wow)"),
        BotCommand(command="/whats_new", description="Get the latest updates"),
    ]

    return commands

async def set_user_commands(user_id: int):
    """Sets default commands for everyone."""
    await bot_instance.set_my_commands(get_default_commands(), BotCommandScopeChat(chat_id=user_id))

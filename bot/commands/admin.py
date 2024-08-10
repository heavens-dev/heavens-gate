from aiogram.types import BotCommandScopeChat, BotCommand
from config.loader import bot_instance
from bot.commands.default import get_default_commands


def get_admin_commands() -> list[BotCommand]:
    commands = get_default_commands()

    commands.extend([
        BotCommand(command="/broadcast", description="Broadcast message to ALL registered users."),
        BotCommand(command="/ban", description="Block user by telegram ID or IP."),
        BotCommand(command="/unban", description="Unblock user by telegram ID or IP. Aliases: pardon, anathem, mercy")
    ])

    return commands

async def set_admin_commands(user_id: int):
    """
    Sets commands menu for admin by user_id
    """
    await bot_instance.set_my_commands(get_admin_commands(), scope=BotCommandScopeChat(chat_id=user_id))

import re
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message


class ClientGettersMiddleware(BaseMiddleware):
    GETTERS_COMMANDS = [
        "ban", "anathem", # ban func
        "unban", "pardon", "mercy", # unban
        "whisper", # broadcast
        "get_user" # get_user
    ]

    async def __call__(
            self,
            handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
            event: Message,
            data: dict[str, Any],
    ) -> Any:
        command: str = re.findall(r"\/(\w+)", event.text)[0]
        if command in self.GETTERS_COMMANDS:
            if len(event.text.split()) <= 1:
                await event.answer("❌ Сообщение должно содержать IP-адрес пользователя или его Telegram ID.")
                return

        return await handler(event, data)
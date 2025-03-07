from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message

from bot.utils.message_utils import send_error_message
from core.logs import bot_logger


class LoggingMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
            event: Message,
            data: dict[str, Any],
    ) -> Any:
        try:
            bot_logger.info(f"User {event.from_user.id} sent message: {event.text}")
            return await handler(event, data)
        except Exception as e:
            await send_error_message(event.chat.id, event.text)
            bot_logger.exception(e)
            return

from aiogram import Router
from aiogram.types import InlineKeyboardButton

from bot.utils.callback_data import GetUserCallbackData
from bot.utils.pagination.base_inline_paginator import \
    BaseInlineKeyboardPaginator
from core.db.db_works import Client, ClientFactory


class UsersInlineKeyboardPaginator(BaseInlineKeyboardPaginator[Client]):
    def __init__(
        self,
        data: list[Client],
        router: Router,
        chat_id: int,
        items_per_page: int = 5,
        current_page: int = 1,
        callback_prefix: str = "page_",
    ) -> None:
        super().__init__(
            data,
            router,
            chat_id,
            items_per_page=items_per_page,
            current_page=current_page,
            callback_prefix=callback_prefix,
        )

    def item_to_button(self, client: Client) -> InlineKeyboardButton:
        return InlineKeyboardButton(
            text=f"{client.userdata.name} ({client.userdata.user_id})",
            callback_data=GetUserCallbackData(
                user_id=client.userdata.user_id
            ).pack()
        )

    def refresh_data(self) -> list[Client]:
        return ClientFactory.select_clients()

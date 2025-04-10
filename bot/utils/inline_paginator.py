from contextlib import suppress
from math import ceil

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup)

from bot.utils.callback_data import GetUserCallbackData
from core.db.db_works import Client, ClientFactory


class UsersInlineKeyboardPaginator:
    goto_previous_page = "⬅️"
    goto_next_page = "➡️"
    goto_first_page = "⏮"
    goto_last_page = "⏭"
    current_page_label = "{} / {}"

    def __init__(self, data: list[Client], router: Router, items_per_page: int = 5, current_page: int = 1, callback_prefix: str = "page_"):
        self.__data = data
        self.router = router
        self.items_per_page = items_per_page
        self.current_page = 1 if current_page < 1 else current_page
        self.max_pages = ceil(len(self.__data) / self.items_per_page)

        self.callback_prefix = callback_prefix

    def __client_to_keyboard_converter(self, client: Client) -> InlineKeyboardButton:
        return InlineKeyboardButton(
            text=f"{client.userdata.name} ({client.userdata.user_id})",
            callback_data=GetUserCallbackData(
                user_id=client.userdata.user_id
            ).pack()
        )

    def __build_keyboard(self, page: int) -> InlineKeyboardMarkup:
        client_buttons = [self.__client_to_keyboard_converter(client) for client in self.data]
        start_index = (page - 1) * self.items_per_page
        end_index = start_index + self.items_per_page

        rows = [[a] for a in client_buttons[start_index:end_index]]

        rows.append([
            InlineKeyboardButton(
                text=self.goto_first_page,
                callback_data=f"{self.callback_prefix}1"
            ),
            InlineKeyboardButton(
                text=self.goto_previous_page,
                callback_data=f"{self.callback_prefix}{page - 1}"
            ),
            InlineKeyboardButton(
                text=self.current_page_label.format(page, self.max_pages),
                callback_data="pass"
            ),
            InlineKeyboardButton(
                text=self.goto_next_page,
                callback_data=f"{self.callback_prefix}{page + 1}"
            ),
            InlineKeyboardButton(
                text=self.goto_last_page,
                callback_data=f"{self.callback_prefix}{self.max_pages}"
            )
        ])

        markup = InlineKeyboardMarkup(inline_keyboard=rows)

        return markup

    def handle_pagination_callback(self):
        async def callback_handler(callback: CallbackQuery) -> None:
            await callback.answer()

            fresh_data = ClientFactory.select_clients()
            self.data = fresh_data
            current_page = int(callback.data.split("_")[-1])

            if current_page < 1:
                current_page = 1
            elif current_page > self.max_pages:
                current_page = self.max_pages

            with suppress(TelegramBadRequest):
                await callback.message.edit_reply_markup(reply_markup=self.__build_keyboard(current_page))

        self.router.callback_query.register(callback_handler, F.data.startswith(self.callback_prefix))

    @property
    def markup(self) -> InlineKeyboardMarkup:
        self.handle_pagination_callback()
        return self.__build_keyboard(self.current_page)

    @property
    def data(self):
        return self.__data

    @data.setter
    def data(self, value: list[Client]) -> None:
        self.__data = value
        self.max_pages = ceil(len(self.__data) / self.items_per_page)

from abc import ABC, abstractmethod
from contextlib import suppress
from math import ceil
from typing import Generic, TypeVar

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup)

T = TypeVar("T")


class BaseInlineKeyboardPaginator(ABC, Generic[T]):
    """Base class for inline keyboard paginators.

    Subclasses must implement `item_to_button()` to convert a data item into an
    inline button with callback data, and may override `refresh_data()` to
    provide fresh data when the page changes (by default the current data is
    reused without hitting the database).

    Each paginator registers itself in a registry keyed by (chat_id, callback_prefix),
    and the callback handler is registered on the router only once per prefix,
    so no handler duplication occurs when paginators are recreated.
    """

    goto_previous_page = "⬅️"
    goto_next_page = "➡️"
    goto_first_page = "⏮"
    goto_last_page = "⏭"
    current_page_label = "{} / {}"

    _active_paginators: dict[tuple[int, str], "BaseInlineKeyboardPaginator"] = {}
    _registered_prefixes: set[tuple[int, str]] = set()

    def __init__(
        self,
        data: list[T],
        router: Router,
        chat_id: int,
        items_per_page: int = 5,
        current_page: int = 1,
        callback_prefix: str = "page_",
    ) -> None:
        self.__data = data
        self.router = router
        self.chat_id = chat_id
        self.items_per_page = items_per_page
        self.current_page = 1 if current_page < 1 else current_page
        self.max_pages = ceil(len(self.__data) / self.items_per_page)
        self.callback_prefix = callback_prefix

        self._active_paginators[(chat_id, callback_prefix)] = self
        self.__register_handler(router, callback_prefix)

    @classmethod
    def __register_handler(cls, router: Router, callback_prefix: str) -> None:
        router_key = (id(router), callback_prefix)
        if router_key in cls._registered_prefixes:
            return
        cls._registered_prefixes.add(router_key)
        router.callback_query.register(
            cls.__handle_pagination_callback,
            F.data.startswith(callback_prefix)
        )

    @classmethod
    async def __handle_pagination_callback(cls, callback: CallbackQuery) -> None:
        prefix = callback.data.rsplit("_", 1)[0] + "_"
        paginator = cls._active_paginators.get((callback.message.chat.id, prefix))
        if paginator is not None:
            await paginator.__process_page_callback(callback)

    async def __process_page_callback(self, callback: CallbackQuery) -> None:
        await callback.answer()

        fresh_data = self.refresh_data()
        self.data = fresh_data

        current_page = int(callback.data.split("_")[-1])

        if current_page < 1:
            current_page = 1
        elif current_page > self.max_pages:
            current_page = self.max_pages

        with suppress(TelegramBadRequest):
            await callback.message.edit_reply_markup(
                reply_markup=self.__build_keyboard(current_page)
            )

    def __build_keyboard(self, page: int) -> InlineKeyboardMarkup:
        item_buttons = [self.item_to_button(item) for item in self.data]
        start_index = (page - 1) * self.items_per_page
        end_index = start_index + self.items_per_page

        rows = [[a] for a in item_buttons[start_index:end_index]]

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

        rows.extend(self._extra_rows())

        return InlineKeyboardMarkup(inline_keyboard=rows)

    def _extra_rows(self) -> list[list[InlineKeyboardButton]]:
        """Additional button rows placed below the pagination row.

        Override in subclasses when extra actions (e.g. manual input) are needed.
        """
        return []

    @abstractmethod
    def item_to_button(self, item: T) -> InlineKeyboardButton:
        """Converts a single data item into an inline button with callback data."""

    def refresh_data(self) -> list[T]:
        """Returns fresh data to redraw the current page. Does not hit the DB by default."""
        return list(self.__data)

    @property
    def markup(self) -> InlineKeyboardMarkup:
        return self.__build_keyboard(self.current_page)

    @property
    def data(self) -> list[T]:
        return self.__data

    @data.setter
    def data(self, value: list[T]) -> None:
        self.__data = value
        self.max_pages = ceil(len(self.__data) / self.items_per_page)

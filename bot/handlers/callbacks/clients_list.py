from contextlib import suppress
from typing import Any

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup)

from bot.utils.callback_data import ClientListCallbackData, GetUserCallbackData
from config.loader import bot_cfg
from core.db.client_queries import ClientSort, StatusFilter, select_users_page
from core.db.enums import ClientStatusChoices, SubscriptionType

router = Router(name="clients_list")

VIEWS: dict[int, ClientListCallbackData] = {}

SORT_LABELS = {
    ClientSort.ID:          "🆔 ID",
    ClientSort.NAME:        "🔤 Имя",
    ClientSort.REGISTERED:  "📅 Дата рег.",
    ClientSort.EXPIRY:      "⌛ Подписка",
}

STATUS_LABELS = {
    StatusFilter.ANY: "Все",
    StatusFilter.BLOCKED: "Заблокированные",
    StatusFilter.ACTIVE: "Активные",
    StatusFilter.EXPIRED: "Истёкшие",
}

STATUS_GLYPHS = {
    ClientStatusChoices.STATUS_CREATED: "✅",
    ClientStatusChoices.STATUS_CONNECTED: "🟢",
    ClientStatusChoices.STATUS_DISCONNECTED: "⚪",
    ClientStatusChoices.STATUS_TIME_EXPIRED: "⏳",
    ClientStatusChoices.STATUS_ACCOUNT_BLOCKED: "🚫",
    ClientStatusChoices.STATUS_IP_BLOCKED: "🚫",
}

NEXT_SUB = {
    None: SubscriptionType.DEFAULT,
    SubscriptionType.DEFAULT: SubscriptionType.CLEAR,
    SubscriptionType.CLEAR: SubscriptionType.ENTERPRISE,
    SubscriptionType.ENTERPRISE: None,
}

NEXT_STATUS = {
    StatusFilter.ANY: StatusFilter.BLOCKED,
    StatusFilter.BLOCKED: StatusFilter.ACTIVE,
    StatusFilter.ACTIVE: StatusFilter.EXPIRED,
    StatusFilter.EXPIRED: StatusFilter.ANY,
}

def sub_label(subscription: SubscriptionType | None) -> str:
    return "Все" if subscription is None else SubscriptionType.to_string(subscription)

def get_last_view(user_id: int) -> ClientListCallbackData:
    return VIEWS.get(user_id, ClientListCallbackData())

def chip(
    cd: ClientListCallbackData,
    text: str,
    style: str | None = None,
    **changes: Any
) -> InlineKeyboardButton:
    return InlineKeyboardButton(
        text=text,
        callback_data=cd.model_copy(update={"page": 1, **changes}).pack(),
        style=style
    )

def sort_chip(cd: ClientListCallbackData, sort: ClientSort) -> InlineKeyboardButton:
    active = cd.sort == sort
    descending = (not cd.descending) if active else sort == ClientSort.REGISTERED
    arrow = ("↓" if cd.descending else "↑") if active else ""
    return chip(
        cd,
        f"{SORT_LABELS[sort]}{arrow}",
        sort=sort, descending=descending,
        style="primary" if active else None
    )

def render_client_list(cd: ClientListCallbackData) -> tuple[str, InlineKeyboardMarkup]:
    page = select_users_page(cd.sort, cd.descending, cd.sub, cd.status, cd.page,
                             cd.page_size)
    cd = cd.model_copy(update={"page": page.page})

    rows = [[sort_chip(cd, ClientSort.ID), sort_chip(cd, ClientSort.NAME),
             sort_chip(cd, ClientSort.REGISTERED), sort_chip(cd, ClientSort.EXPIRY)]]

    rows.append([
        chip(cd, sub_label(cd.sub), sub=NEXT_SUB[cd.sub],
             style="primary" if cd.sub is not None else None),
        chip(cd, STATUS_LABELS[cd.status], status=NEXT_STATUS[cd.status],
             style="primary" if cd.status != StatusFilter.ANY else None),
    ])

    for user in page.items:
        rows.append([InlineKeyboardButton(
            text=f"{STATUS_GLYPHS[user.status]} {user.name} ({user.user_id})",
            callback_data=GetUserCallbackData(user_id=user.user_id).pack()
        )])

    rows.append([
        chip(cd, "⏮", page=1),
        chip(cd, "⬅️", page=page.page - 1),
        InlineKeyboardButton(text=f"{page.page} / {page.pages}", callback_data="pass"),
        chip(cd, "➡️", page=page.page + 1),
        chip(cd, "⏭", page=page.pages),
    ])

    text = (f"👥 <b>Пользователи</b> - найдено: <b>{page.total}</b>\n"
            f"Сортировка: {SORT_LABELS[cd.sort]} {'↓' if cd.descending else '↑'} // "
            f"Подписка: {sub_label(cd.sub)} // Статус: {STATUS_LABELS[cd.status]}")

    return text, InlineKeyboardMarkup(inline_keyboard=rows)

@router.callback_query(ClientListCallbackData.filter(), F.from_user.id.in_(bot_cfg.admins))
async def clients_list_callback(callback: CallbackQuery, callback_data: ClientListCallbackData):
    await callback.answer()

    VIEWS[callback.from_user.id] = callback_data

    text, markup = render_client_list(callback_data)
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(text, reply_markup=markup)

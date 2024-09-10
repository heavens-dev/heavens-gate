import os
import re
import sys
from typing import Optional

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.handlers.keyboards import (build_user_actions_keyboard,
                                    preview_keyboard)
from bot.middlewares.client_getters_middleware import ClientGettersMiddleware
from bot.utils.states import PreviewMessageStates
from bot.utils.user_helper import get_user_data_string
from config.loader import bot_cfg, bot_instance
from core.db.db_works import Client, ClientFactory
from core.db.enums import StatusChoices

router = Router(name="admin")
router.message.filter(
    F.from_user.id.in_(bot_cfg.admins)
)
router.message.middleware(ClientGettersMiddleware())


async def preview_message(msg: str, chat_id: int, state: FSMContext, clients_list: list[int]):
    await state.set_state(PreviewMessageStates.preview)
    await state.set_data(data=dict(message=msg, user_ids=clients_list))

    await bot_instance.send_message(chat_id=chat_id, text=
        "✉️ <b>Проверь правильность твоего сообщения перед отправкой</b>.\n"
        + "\n--------------------------------------------\n"
        + msg
        + "\n--------------------------------------------"
        + "\n<b>Отправить?</b>",
        reply_markup=preview_keyboard()
    )

@router.message(Command("reboot"))
async def reboot(message: Message) -> None:
    await message.answer("Бот перезапускается...")

    await message.chat.do("choose_sticker")

    with open(".reboot", "w", encoding="utf-8") as f:
        f.write(str(message.chat.id))

    os.execv(sys.executable, ['python'] + sys.argv)

@router.message(Command("broadcast"))
async def broadcast(message: Message, state: FSMContext):
    args = message.html_text.split()

    if len(args) <= 1:
        await message.answer("❌ Сообщение должно содержать хотя бы какой-то текст для отправки.")
        return

    clients_list = []
    all_clients = ClientFactory.select_clients()
    msg = message.html_text.split(maxsplit=1)[1]

    for client in all_clients:
        if message.chat.id == client.userdata.telegram_id:
            continue
        clients_list.append(client.userdata.telegram_id)

    await preview_message(msg, message.chat.id, state, clients_list)

@router.message(Command("whisper"))
async def whisper(message: Message, state: FSMContext, client: Client):
    args = message.html_text.split()

    if len(args) <= 2:
        await message.answer("❌ Сообщение должно содержать хотя бы какой-то текст для отправки.")
        return

    msg = message.html_text.split(maxsplit=2)[2]

    await preview_message(msg, message.chat.id, state, [client.userdata.telegram_id])

@router.message(Command("ban", "anathem"))
async def ban(message: Message, client: Client):
    client.set_status(StatusChoices.STATUS_ACCOUNT_BLOCKED)
    await message.answer(
        f"✅ Пользователь <code>{client.userdata.name}:{client.userdata.telegram_id}:{client.userdata.ip_address}</code> заблокирован."
    )
    # TODO: notify user about blocking and reject any ongoing connections

@router.message(Command("unban", "mercy", "pardon"))
async def unban(message: Message, client: Client):
    client.set_status(StatusChoices.STATUS_CREATED)
    await message.answer(
        f"✅ Пользователь <code>{client.userdata.name}:{client.userdata.telegram_id}:{client.userdata.ip_address}</code> разблокирован."
    )
    # TODO: notify user about pardon

@router.message(Command("get_user"))
async def get_user(message: Message, client: Client):
    await message.answer(f"Пользователь: {client.userdata.name}")
    await message.answer(
        get_user_data_string(client),
        reply_markup=build_user_actions_keyboard(client)
    )

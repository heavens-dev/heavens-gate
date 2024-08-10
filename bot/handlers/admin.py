from typing import Optional
import sys
import os
from aiogram.filters import Command
from aiogram.types import Message
from aiogram import Router, F

from core.db.db_works import ClientFactory, Client
from core.utils.check import check_ip_address
from core.db.enums import StatusChoices
from config.loader import bot_cfg


admin_router = Router()
admin_router.message.filter(
    F.from_user.id.in_(bot_cfg.admins)
)

async def get_client_by_id_or_ip(message: Message) -> Optional[Client]:
    """Not a command"""
    args = message.text.split()
    if len(args) <= 1:
        await message.answer("❌ Сообщение должно содержать IP адрес пользователя или его Telegram ID.")
        return None
    
    if check_ip_address(args[1]):
        client = ClientFactory.get_client(args[1])
    else:
        client = ClientFactory(tg_id=args[1]).get_client()

    if client is None:
        await message.answer(f"❌ Пользователь <code>{args[1]}</code> не найден.", parse_mode="HTML")
        return None
    return client

@admin_router.message(Command("reboot"))
async def reboot(message: Message) -> None:
    await message.answer("Бот перезапускается...")

    await message.chat.do("choose_sticker")

    with open(".reboot", "w", encoding="utf-8") as f:
        f.write(str(message.chat.id))

    os.execv(sys.executable, ['python'] + sys.argv)

@admin_router.message(Command("broadcast"))
async def broadcast(message: Message):
    """Broadcast message to ALL registered users"""
    args = message.text.split()
    if len(args) <= 1:
        await message.answer("❌ Сообщение должно содержать хотя бы какой-то текст для отправки.")
        return
    all_clients = ClientFactory.select_clients()
    text = "✉️ <b>Рассылка от администрации</b>:\n\n"
    text += " ".join(args[1::])
    # ? sooo we can get rate limited probably. fixme? maybe later.
    for client in all_clients:
        if message.chat.id == client.userdata.telegram_id:
            continue
        await message.bot.send_message(client.userdata.telegram_id, text, parse_mode="HTML")
    await message.answer("Сообщение транслировано всем пользователям.")

@admin_router.message(Command("ban"))
async def ban(message: Message):
    client = await get_client_by_id_or_ip(message)

    if not client: return

    client.set_status(StatusChoices.STATUS_ACCOUNT_BLOCKED)
    await message.answer(
        f"✅ Пользователь <code>{client.userdata.name}:{client.userdata.telegram_id}:{client.userdata.ip_address}</code> заблокирован.",
        parse_mode="HTML")
    # TODO: notify user about blocking and reject any ongoing connections

@admin_router.message(Command("unban", "mercy", "anathem", "pardon"))
async def unban(message: Message):
    client = await get_client_by_id_or_ip(message)
    
    if not client: return

    client.set_status(StatusChoices.STATUS_CREATED)
    await message.answer(
        f"✅ Пользователь <code>{client.userdata.name}:{client.userdata.telegram_id}:{client.userdata.ip_address}</code> разблокирован.",
        parse_mode="HTML")
    # TODO: notify user about pardon

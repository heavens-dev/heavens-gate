import sys
import os
from aiogram.filters import Command
from aiogram.types import Message

from bot.utils.user_helper import get_client_by_id_or_ip
from config.loader import bot_instance, admin_router
from core.db.db_works import ClientFactory
from core.db.enums import StatusChoices


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

@admin_router.message(Command("whisper"))
async def whisper(message: Message):
    client = await get_client_by_id_or_ip(message)

    if not client: return

    args = message.text.split()
    if len(args) <= 2:
        await message.answer("❌ Сообщение должно содержать хотя бы какой-то текст для отправки.")
        return

    await bot_instance.send_message(
        client.userdata.telegram_id, 
        text="🤫 <b>Сообщение от администрации</b>:\n\n" + "".join(i for i in message.text.split()[2::]),
        parse_mode="HTML"
    )
    await message.answer("✅ Сообщение отправлено.")

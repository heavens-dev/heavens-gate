import asyncio
import os
import sys

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.handlers.keyboards import build_user_actions_keyboard, cancel_keyboard
from bot.middlewares.client_getters_middleware import ClientGettersMiddleware
from bot.utils.inline_paginator import UsersInlineKeyboardPaginator
from bot.utils.message_utils import preview_message
from bot.utils.states import AddPeerStates, WhisperStates
from bot.utils.user_helper import get_user_data_string
from config.loader import bot_cfg, ip_queue, wghub
from core.db.db_works import Client, ClientFactory
from core.db.enums import ClientStatusChoices, PeerStatusChoices
from core.logs import bot_logger

router = Router(name="admin")
router.message.filter(
    F.from_user.id.in_(bot_cfg.admins)
)
router.message.middleware(ClientGettersMiddleware())


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
        if message.chat.id == client.userdata.user_id:
            continue
        clients_list.append(client.userdata.user_id)

    await preview_message(msg, message.chat.id, state, clients_list)

@router.message(Command("whisper"))
async def whisper(message: Message, client: Client, state: FSMContext):
    args = message.html_text.split()

    if len(args) <= 2:
        await state.set_data({"user_id": client.userdata.user_id})
        await state.set_state(WhisperStates.message_entering)
        await message.answer("✏️ Введи сообщение:", reply_markup=cancel_keyboard())
        return

    msg = message.html_text.split(maxsplit=2)[2]

    await preview_message(msg, message.chat.id, state, [client.userdata.user_id])

@router.message(Command("ban", "anathem"))
async def ban(message: Message, client: Client):
    client.set_status(ClientStatusChoices.STATUS_ACCOUNT_BLOCKED)
    await message.answer(
        f"✅ Пользователь <code>{client.userdata.name}:{client.userdata.user_id}:{client.userdata.ip_address}</code> заблокирован."
    )
    # TODO: notify user about blocking and reject any ongoing connections

@router.message(Command("unban", "mercy", "pardon"))
async def unban(message: Message, client: Client):
    client.set_status(ClientStatusChoices.STATUS_CREATED)
    await message.answer(
        f"✅ Пользователь <code>{client.userdata.name}:{client.userdata.user_id}:{client.userdata.ip_address}</code> разблокирован."
    )
    # TODO: notify user about pardon

@router.message(Command("get_user"))
async def get_user(message: Message, client: Client):
    await message.answer(f"Пользователь: {client.userdata.name}")
    await message.answer(
        get_user_data_string(client),
        reply_markup=build_user_actions_keyboard(client)
    )

@router.message(Command("add_peer"))
async def add_peer(message: Message, client: Client, state: FSMContext):
    last_id = ClientFactory.get_latest_peer_id()

    await message.answer("ℹ️ Выбери протокол")

    await state.set_state(AddPeerStates.select_protocol)

    # try:
    #     ip_addr = ip_queue.get_ip()
    # except Exception:
    #     await message.answer("❌ Нет доступных IP-адресов!")
    #     bot_logger.critical("❌ Tried to add a peer, but no IP addresses are available.")
    #     return
    # new_peer = client.add_wireguard_peer(shared_ips=ip_addr, peer_name=f"{client.userdata.name}_{last_id}", is_amnezia=wghub.is_amnezia)
    # wghub.add_peer(new_peer)
    # with bot_logger.contextualize(peer=new_peer):
    #     bot_logger.info(f"New peer was created manually by {message.from_user.username}")
    # await message.answer("✅ Пир создан и добавлен в конфиг.")

# TODO: split this command into two separate commands
@router.message(Command("disable_peer", "enable_peer"))
async def manage_peer(message: Message):
    if len(message.text.split()) <= 1:
        await message.answer("❌ Сообщение должно содержать IP адрес пира.")
        return

    ip = message.text.split()[1]
    is_disable = message.text.startswith("/disable")

    peer = ClientFactory.get_peer(ip)
    if not peer:
        await message.answer("❌ IP-адрес не найден.")
        return

    client = ClientFactory(user_id=peer.user_id).get_client()
    if is_disable:
        client.set_peer_status(peer.id, PeerStatusChoices.STATUS_BLOCKED)
        wghub.disable_peer(peer)
        await message.answer("✅ Пир отключён.")
        await message.bot.send_message(
            client.userdata.user_id,
            f"‼️ Пир {peer.peer_name} был принудительно заблокирован. Обратись к администрации, чтобы уточнить детали."
        )
        bot_logger.info(f"Peer (IP: {peer.shared_ips}) was blocked by {message.from_user.username}")
    else:
        client.set_peer_status(peer.id, PeerStatusChoices.STATUS_DISCONNECTED)
        wghub.enable_peer(peer)
        await message.answer("✅ Пир включён.")
        await message.bot.send_message(
            client.userdata.user_id,
            f"‼️ Пир {peer.peer_name} был разблокирован. Можешь начать пользоваться в течение короткого времени."
        )
        bot_logger.info(f"Peer (IP: {peer.shared_ips}) was unblocked by {message.from_user.username}")

# TODO: delete peer also by peer_id
@router.message(Command("delete_peer"))
async def delete_peer(message: Message):
    splitted_message = message.text.split()
    if len(splitted_message) <= 1:
        await message.answer("❌ Сообщение должно содержать IP адрес пира.")
        return
    ip_address = splitted_message[1]

    peer = ClientFactory.get_peer(ip_address)
    if not peer:
        await message.answer("❌ IP-адрес не найден.")
        return

    wghub.delete_peer(peer)
    ClientFactory.delete_peer(peer)
    ip_queue.release_ip(peer.shared_ips)
    await message.answer("✅ Пир был успешно удалён.")
    with bot_logger.contextualize(peer=peer):
        bot_logger.info(f"Peer (IP: {peer.shared_ips}) was deleted by {message.from_user.username}")

@router.message(Command("syncconfig"))
async def syncconfig(message: Message):
    wghub.sync_config()
    bot_logger.info(f"Wireguard config was forcefully synchronized by {message.from_user.id}")
    await message.answer("✅ Конфиг Wireguard был синхронизирован с сервером.")

@router.message(Command("users"))
async def users(message: Message):
    all_clients = ClientFactory.select_clients()
    paginator = UsersInlineKeyboardPaginator(all_clients, router)
    msg = await message.answer("Список всех пользователей:", reply_markup=paginator.markup)
    await asyncio.sleep(60)
    await msg.delete()

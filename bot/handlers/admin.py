import asyncio
import datetime
import os
import sys
import tempfile
from pathlib import Path

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, Message

from bot.handlers.keyboards import (build_protocols_keyboard,
                                    build_user_actions_keyboard,
                                    cancel_keyboard)
from bot.middlewares.client_getters_middleware import ClientGettersMiddleware
from bot.middlewares.logging_middleware import LoggingMiddleware
from bot.utils.inline_paginator import UsersInlineKeyboardPaginator
from bot.utils.message_utils import preview_message
from bot.utils.states import AddPeerStates, WhisperStates
from bot.utils.user_helper import get_user_data_string
from config.loader import (bot_cfg, cfg, connections_observer, db_cfg,
                           ip_queue, wghub, xray_worker)
from core.db.db_works import Client, ClientFactory
from core.db.enums import ClientStatusChoices, PeerStatusChoices, ProtocolType
from core.logs import bot_logger
from core.utils.ip_utils import check_ip_address
from core.utils.peers_utils import disable_peers, enable_peers
from export_clients_csv import export_clients_dump

router = Router(name="admin")
router.message.filter(
    F.from_user.id.in_(bot_cfg.admins)
)
router.message.middleware.register(ClientGettersMiddleware())
router.message.middleware.register(LoggingMiddleware())


@router.message(Command("dump"))
async def dump_clients(message: Message):
    layout = "canary" if cfg.is_canary else "master"
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_name = f"clients_dump_{layout}_{timestamp}.csv"

    status_message = await message.answer("🗂️ Подготавливаю CSV-дамп клиентов...")

    try:
        with tempfile.TemporaryDirectory(prefix="hg_dump_") as temp_dir:
            output_path = Path(temp_dir) / output_name

            clients_count, resolved_layout, _ = await asyncio.to_thread(
                export_clients_dump,
                output_path=output_path,
                db_path=db_cfg.path,
                layout=layout,
            )

            dump_bytes = output_path.read_bytes()

        await message.answer_document(
            document=BufferedInputFile(file=dump_bytes, filename=output_name),
            caption=(
                f"✅ Дамп готов. Пользователей: {clients_count}. "
                f"Режим: {resolved_layout}."
            ),
        )
        await status_message.delete()
    except Exception as exc:
        bot_logger.exception(f"Couldn't create clients dump: {exc}")
        await status_message.edit_text("❌ Не удалось создать дамп. Проверь логи ядра.")


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
    peers = client.get_all_peers(protocol_specific=True)
    disable_peers(wghub, xray_worker, peers, client)

    await message.answer(
        f"✅ Пользователь <code>{client.userdata.name}:{client.userdata.user_id}</code> заблокирован."
    )
    await message.bot.send_message(
        client.userdata.user_id,
        f"🔒❗ Твой аккаунт был заблокирован. Если тебе необходима информация или ты считаешь, что это ошибка, "
        "свяжись с нами для дальшейшего разбирательства."
    )

@router.message(Command("unban", "mercy", "pardon"))
async def unban(message: Message, client: Client):
    client.set_status(ClientStatusChoices.STATUS_CREATED)
    peers = client.get_all_peers(protocol_specific=True)
    enable_peers(wghub, xray_worker, peers, client)
    await message.answer(
        f"✅ Пользователь <code>{client.userdata.name}:{client.userdata.user_id}</code> разблокирован."
    )
    await message.bot.send_message(
        client.userdata.user_id,
        f"🔓❗ Твой аккаунт был разблокирован. Если у тебя были доступные пиры, они станут доступны в ближайшее время."
    )

@router.message(Command("get_user"))
async def get_user(message: Message, client: Client):
    await message.answer(f"Пользователь: {client.userdata.name}")
    user_string = get_user_data_string(client, show_peer_ids=True)
    await message.answer(user_string[0])
    await message.answer(user_string[1], reply_markup=build_user_actions_keyboard(client))

@router.message(Command("add_peer"))
async def add_peer(message: Message, client: Client, state: FSMContext):
    keyboard = build_protocols_keyboard()
    keyboard.inline_keyboard.append(cancel_keyboard().inline_keyboard[0])

    await message.answer("ℹ️ Выбери протокол", reply_markup=keyboard)

    await state.set_state(AddPeerStates.select_protocol)
    await state.set_data({
        "user_id": client.userdata.user_id,
    })

# ? writing "command" in the function name to avoid potential name conflicts
@router.message(Command("disable_peer"))
async def disable_peer_command(message: Message):
    if len(message.text.split()) <= 1:
        await message.answer("❌ Сообщение должно содержать ID или IP-адрес пира (если это пир Wireguard).")
        return

    id_or_ip = message.text.split()[1]

    if check_ip_address(id_or_ip):
        peer = ClientFactory.get_peer_by_ip(id_or_ip)
    else:
        peer = ClientFactory.get_peer_by_id(id_or_ip, protocol_specific=True)

    if not peer:
        await message.answer("❌ Пир не найден.")
        return

    client = ClientFactory(user_id=peer.user_id).get_client()
    match peer.peer_type:
        case ProtocolType.WIREGUARD | ProtocolType.AMNEZIA_WIREGUARD:
            wghub.disable_peer(peer)
        case ProtocolType.XRAY:
            xray_worker.disable_peer(peer, expire_time=client.userdata.expire_time)
        case _:
            bot_logger.warning(f"Unknown peer type: {peer.peer_type}. Can't disable peer.")
            await message.answer("❌ Неподдерживаемый тип пира. Странно...")
            return
    client.set_peer_status(peer.peer_id, PeerStatusChoices.STATUS_BLOCKED)
    await message.answer("✅ Пир отключён.")
    await message.bot.send_message(
        client.userdata.user_id,
        f"‼️ Пир {peer.peer_name} был принудительно заблокирован. Обратись к администрации, чтобы уточнить детали."
    )

    with bot_logger.contextualize(peer=peer):
        bot_logger.info(f"Peer was blocked by {message.from_user.username}.")

@router.message(Command("enable_peer"))
async def enable_peer_command(message: Message):
    if len(message.text.split()) <= 1:
        await message.answer("❌ Сообщение должно содержать ID или IP адрес пира (если это пир Wireguard).")
        return

    id_or_ip = message.text.split()[1]

    if check_ip_address(id_or_ip):
        peer = ClientFactory.get_peer_by_ip(id_or_ip)
    else:
        peer = ClientFactory.get_peer_by_id(id_or_ip, protocol_specific=True)

    if not peer:
        await message.answer("❌ Пир не найден.")
        return

    client = ClientFactory(user_id=peer.user_id).get_client()
    match peer.peer_type:
        case ProtocolType.WIREGUARD | ProtocolType.AMNEZIA_WIREGUARD:
            wghub.enable_peer(peer)
        case ProtocolType.XRAY:
            xray_worker.enable_peer(peer, expire_time=client.userdata.expire_time)
        case _:
            bot_logger.warning(f"Unknown peer type: {peer.peer_type}. Can't enable peer.")
            await message.answer("❌ Неподдерживаемый тип пира. Странно...")
            return
    client.set_peer_status(peer.peer_id, PeerStatusChoices.STATUS_DISCONNECTED)
    await message.answer("✅ Пир включён.")
    await message.bot.send_message(
        client.userdata.user_id,
        f"‼️ Пир {peer.peer_name} был разблокирован. Можешь начать пользоваться в течение короткого времени."
    )

    with bot_logger.contextualize(peer=peer):
        bot_logger.info(f"Peer was unblocked by {message.from_user.username}.")

# TODO minor: reimplement deleting by IP address for Wireguard peers
@router.message(Command("delete_peer"))
async def delete_peer(message: Message):
    splitted_message = message.text.split()
    if len(splitted_message) <= 1:
        await message.answer("❌ Сообщение должно содержать ID пира.")
        return
    peer_id = splitted_message[1]

    peer = ClientFactory.delete_peer_by_id(int(peer_id), protocol_specific=True)

    if not peer:
        await message.answer("❌ Пир не найден.")
        return

    if peer.peer_type in (ProtocolType.WIREGUARD, ProtocolType.AMNEZIA_WIREGUARD):
        wghub.delete_peer(peer)
        ip_queue.release_ip(peer.shared_ips)
    elif peer.peer_type == ProtocolType.XRAY:
        xray_worker.delete_peer(peer)

    await message.answer("✅ Пир был успешно удалён.")
    with bot_logger.contextualize(peer=peer):
        bot_logger.info(f"Peer was deleted by {message.from_user.username}")

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

@router.message(Command("listen_clients"))
async def listen_clients(message: Message):
    connected_only = True
    if len(message.text.split()) > 1:
        if "false" in message.text.lower():
            connected_only = False
    msg = await message.answer(
        "🔂 Запущена прослушка" + (" всех" if connected_only is False else "") + " соединений..."
    )
    await connections_observer.run_check_connections(connected_only)
    await msg.edit_text("✅ Задание завершено!")

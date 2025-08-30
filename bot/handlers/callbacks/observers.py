import datetime
import time

from aiogram import Router

from config.loader import bot_instance, connections_observer, interval_observer
from core.db.db_works import Client
from core.db.model_serializer import BasePeer
from core.logs import bot_logger
from core.monitoring.metrics import (CONNECT_EVENTS, DISCONNECT_EVENTS,
                                     TIMEOUT_EVENTS)

router = Router(name="observers")


@connections_observer.startup()
async def on_connections_observer_startup():
    bot_logger.info("Observer is running!")

@connections_observer.connected()
async def on_connected(client: Client, peer: BasePeer):
    with bot_logger.contextualize(client=client, peer=peer):
        bot_logger.info("Client connected")
    CONNECT_EVENTS.inc(1)

@connections_observer.disconnected()
async def on_disconnected(client: Client, peer: BasePeer):
    with bot_logger.contextualize(client=client, peer=peer):
        bot_logger.info("Client disconnected")
    DISCONNECT_EVENTS.inc(1)

@connections_observer.timer_observer()
async def warn_user_timeout(client: Client, peer: BasePeer, disconnect: bool):
    time_left = peer.peer_timer - datetime.datetime.now()
    delta_as_time = time.gmtime(time_left.total_seconds())
    # TODO: write an ip address with a peer name
    await bot_instance.send_message(client.userdata.user_id,
        (f"⚠️ Подключение {peer.peer_name} будет разорвано через {delta_as_time.tm_min} минут. "
        if not disconnect else
        f"❗ Подключение {peer.peer_name} было разорвано из-за неактивности. ") +
        "Введи /unblock, чтобы обновить время действия подключения.")
    if disconnect:
        TIMEOUT_EVENTS.inc(1)

@interval_observer.expire_date_warning_observer()
async def warn_user_expire_date(client: Client):
    await bot_instance.send_message(client.userdata.user_id,
        "⚠️ Твой аккаунт будет заблокирован через 24 часа из-за истечения оплаченного времени. "
        "Свяжись с администрацией для продления доступа."
    )

@interval_observer.expire_date_block_observer()
async def block_user_expire_date(client: Client):
    await bot_instance.send_message(client.userdata.user_id,
        "❌ Твой аккаунт заблокирован из-за истечения оплаченного времени. "
        "Если ты хочешь продлить доступ, свяжись с нами."
    )

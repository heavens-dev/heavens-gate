import datetime
import time

from aiogram import Router

from config.loader import bot_instance, connections_observer, interval_observer
from core.db.db_works import Client
from core.db.enums import SubscriptionType
from core.db.model_serializer import BasePeer, Organization, User
from core.logs import bot_logger

router = Router(name="observers")


@connections_observer.startup()
async def on_connections_observer_startup():
    bot_logger.info("Observer is running!")

@connections_observer.connected()
async def on_connected(client: Client, peer: BasePeer):
    with bot_logger.contextualize(client=client, peer=peer):
        bot_logger.info("Client connected")

@connections_observer.disconnected()
async def on_disconnected(client: Client, peer: BasePeer):
    with bot_logger.contextualize(client=client, peer=peer):
        bot_logger.info("Client disconnected")

@connections_observer.timer_observer()
async def warn_user_timeout(client: Client, peer: BasePeer, disconnect: bool):
    time_left = peer.active_until - datetime.datetime.now()
    delta_as_time = time.gmtime(time_left.total_seconds())
    # TODO: write an ip address with a peer name
    await bot_instance.send_message(client.userdata.user_id,
        (f"⚠️ Подключение {peer.name} будет разорвано через {delta_as_time.tm_min} минут. "
        if not disconnect else
        f"❗ Подключение {peer.name} было разорвано из-за неактивности. ") +
        "Введи /unblock, чтобы обновить время действия подключения.")

@interval_observer.expire_date_warning_observer()
async def warn_user_expire_date(client: Client):
    if client.userdata.subscription_type == SubscriptionType.ENTERPRISE:
        return
    await bot_instance.send_message(client.userdata.user_id,
        "⚠️ Твой аккаунт будет заблокирован через 24 часа из-за истечения оплаченного времени. "
        "Свяжись с администрацией для продления доступа."
    )

@interval_observer.expire_date_block_observer()
async def block_user_expire_date(client: Client):
    if client.userdata.subscription_type == SubscriptionType.ENTERPRISE:
        return
    await bot_instance.send_message(client.userdata.user_id,
        "❌ Твой аккаунт заблокирован из-за истечения оплаченного времени. "
        "Если ты хочешь продлить доступ, свяжись с нами."
    )

@interval_observer.organization_expire_date_warning_observer()
async def warn_organization_expire_date(user: User, org: Organization, days_left: int):
    await bot_instance.send_message(user.user_id,
        f'⚠️ Время действия подписки вашей организации "{org.name}" истекает через {days_left} дней. '
        'Свяжитесь с администрацией или ответственными лицами вашей организации для продления подписки.\n\n'
        '(вы получаете это сообщение, так как являетесь владельцем или ответственным лицом организации в сервисе)'
    )

@interval_observer.organization_expire_date_block_observer()
async def block_organization_expire_date(user: User, org: Organization):
    await bot_instance.send_message(user.user_id,
        f'❌ Время действия подписки вашей организации "{org.name}" истекло. '
        'Все пользователи организации были заблокированы и более не могут использовать сервис без продления.\n\n'
        '(вы получаете это сообщение, так как являетесь владельцем или ответственным лицом организации в сервисе)'
    )

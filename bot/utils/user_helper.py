import datetime
from typing import Optional, Union

import humanize
from aiogram.types import BufferedInputFile
from pydantic import ValidationError

from config.loader import (connections_observer, core_cfg, wghub,
                           wireguard_server_config, xray_worker)
from core.db.db_works import Client, ClientFactory
from core.db.enums import (ClientStatusChoices, PeerStatusChoices,
                           ProtocolType, SubscriptionType)
from core.db.model_serializer import WireguardPeer, XrayPeer
from core.logs import bot_logger
from core.wg.wgconfig_helper import get_peer_config_str
from core.xray.xray_worker import XrayWorker


# TODO: make this function accept ip addresses again
def get_client_by_id_or_ip(user_id: Union[str, int]) -> tuple[Optional[Client], Optional[str]]:
    """Tries to get client by it's id.

    Returns:
        tuple: `(Client, None)` if the user was found, `(None, "error_message")` otherwise"""
    try:
        client = ClientFactory(user_id=user_id).get_client()
    except ValidationError:
        client = None

    if client is None:
        return None, f"❌ Пользователь <code>{user_id}</code> не найден."
    return client, None

def get_user_data_string(client: Client, show_peer_ids: bool = False) -> list[str]:
    """Returns human-readable data about User. Recommended to use `parse_mode="HTML"`.

    Note:
        Telegram has a limit of 512 bytes for a single message, so text is separated into two parts:
        - Static user info (ID, registration date, etc.)
        - Peers info, client status and expiration date
    """
    peers = client.get_all_peers(protocol_specific=True)
    peers_str = ""
    time_limitation = core_cfg.is_time_limit_disabled()
    has_xray_peers = any(peer.type == ProtocolType.XRAY for peer in peers)

    for peer in peers:
        if show_peer_ids:
            peers_str += f"({peer.peer_id}) "
        match peer.type:
            case ProtocolType.WIREGUARD | ProtocolType.AMNEZIA_WIREGUARD:
                peers_str += "[Wireguard] " if peer.type == ProtocolType.WIREGUARD else "[Amnezia WG] "
                peers_str += f"{peer.name or peer.shared_ips}: {PeerStatusChoices.to_string(peer.status)} ({peer.shared_ips}) "
            case ProtocolType.XRAY:
                peers_str += f"[XRay] {peer.name or peer.flow}: {PeerStatusChoices.to_string(peer.status)} "
        if peer.status == PeerStatusChoices.STATUS_CONNECTED \
           and not time_limitation:
            timer = datetime.datetime.strftime(peer.active_until, "%H:%M")
            peers_str += f"(активен до {timer})"
        peers_str += "\n"

    if client.userdata.subscription_expiry:
        expire_time = f'До: {client.userdata.subscription_expiry.strftime("%d.%m.%Y")}\n'
        if client.userdata.subscription_expiry > datetime.datetime.now():
            expire_time += f'Осталось времени: {humanize.naturaldelta(client.userdata.subscription_expiry - datetime.datetime.now())}'
        else:
            expire_time += "❌ Время истекло"
    else:
        expire_time = "❌ Не оплачено"

    if client.userdata.subscription_type:
        subscription_type = SubscriptionType.to_string(client.userdata.subscription_type)
    else:
        subscription_type = "❌ Не оплачено"

    if has_xray_peers:
        link = xray_worker.get_subscription_link(client.userdata.vless_sub_token)
    else:
        link = "Нет доступных конфигураций!"


    return [f"""ℹ️ <b>Информация об аккаунте</b>:
<b>ID</b>: <code>{client.userdata.user_id}</code>
📅 <b>Дата регистрации</b>: {client.userdata.registered_at.strftime("%d.%m.%Y в %H:%M")}
""",
f"""<b>Текущий статус</b>: {ClientStatusChoices.to_string(client.userdata.status)}
🕓 <b>Статус оплаты</b>:
<blockquote>Подписка: {subscription_type}
{expire_time}</blockquote>

🌐 <b>Ссылка на подписку</b>:
{link}

🛜 <b>Пиры</b>:
{peers_str or '❌ Нет пиров\n'}
"""]

def extend_users_subscription_time(client: Client, time_to_add: datetime.timedelta) -> bool:
    now = datetime.datetime.now()

    if not isinstance(client.userdata.subscription_expiry, datetime.datetime) or client.userdata.subscription_expiry < now:
        client.userdata.subscription_expiry = now

    is_updated = client.set_subscription_expiry(client.userdata.subscription_expiry + time_to_add)

    if not is_updated:
        bot_logger.error(f"Couldn't update expire time for user {client.userdata.user_id}!")
        return False

    if xray_peers := client.get_xray_peers():
        for peer in xray_peers:
            xray_worker.update_peer(
                peer,
                expiry_time=client.userdata.subscription_expiry,

            )

    return True

@bot_logger.catch()
def unblock_timeout_connections(client: Client) -> bool:
    peers = client.get_all_peers(protocol_specific=True)
    for peer in peers:
        match peer.status:
            case PeerStatusChoices.STATUS_TIME_EXPIRED:
                if peer.type in [ProtocolType.WIREGUARD, ProtocolType.AMNEZIA_WIREGUARD]:
                    peer: WireguardPeer
                    wghub.enable_peer(peer)
                elif peer.type == ProtocolType.XRAY:
                    peer: XrayPeer
                    xray_worker.enable_peer(peer, expire_time=client.userdata.subscription_expiry)
                client.set_peer_status(peer.peer_id, PeerStatusChoices.STATUS_DISCONNECTED)
                client.set_status(ClientStatusChoices.STATUS_DISCONNECTED)
            case PeerStatusChoices.STATUS_CONNECTED:
                new_time = datetime.datetime.now() + datetime.timedelta(hours=core_cfg.peer_active_time)
                client.set_peer_timer(peer.peer_id, time=new_time)
    # updating peer timer for observer
    connections_observer.update_client_peers(client)

    return True


def get_peer_as_input_file(peer: WireguardPeer) -> BufferedInputFile:
    interface_args = {}
    if peer.is_amnezia:
        interface_args = {
            "Jc": peer.Jc,
            "Jmin": peer.Jmin,
            "Jmax": peer.Jmax,
            "Junk": wireguard_server_config.junk
        }

    return BufferedInputFile(
        file=bytes(get_peer_config_str(wireguard_server_config, peer, interface_args), encoding="utf-8"),
        filename=f"{peer.name or peer.peer_id}.conf"
    )

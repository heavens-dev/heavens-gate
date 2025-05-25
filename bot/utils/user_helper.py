import datetime
from typing import Optional, Union

import humanize
from aiogram.types import BufferedInputFile
from pydantic import ValidationError

from config.loader import core_cfg, wghub, wireguard_server_config, xray_worker
from core.db.db_works import Client, ClientFactory
from core.db.enums import ClientStatusChoices, PeerStatusChoices, ProtocolType
from core.db.model_serializer import WireguardPeer, XrayPeer
from core.logs import bot_logger
from core.utils.ip_utils import check_ip_address
from core.wg.wgconfig_helper import get_peer_config_str


# TODO: remove deprecated "ip_address" argument, since it was never used
def get_client_by_id_or_ip(id_or_ip: Union[str, int]) -> tuple[Optional[Client], Optional[str]]:
    """Tries to get client by it's id or ip.
    Returns `(Client, None)` if the user was found, `(None, "error_message")` otherwise"""
    if check_ip_address(id_or_ip):
        client = ClientFactory.get_client(id_or_ip)
    else:
        try:
            client = ClientFactory(user_id=id_or_ip).get_client()
        except ValidationError:
            client = None

    if client is None:
        return None, f"❌ Пользователь <code>{id_or_ip}</code> не найден."
    return client, None

def get_user_data_string(client: Client, show_peer_ids: bool = False) -> list[str]:
    """Returns human-readable data about User. Recommended to use `parse_mode="HTML"`.

    Note:
        Telegram has a limit of 512 bytes for a single message, so text is separeted into two parts:
        - Static user info (ID, registration date, etc.)
        - Peers info, client status and expiration date
    """
    peers = client.get_all_peers(serialized=True)
    peers_str = ""

    for peer in peers:
        if show_peer_ids:
            peers_str += f"({peer.peer_id}) "
        match peer.peer_type:
            case ProtocolType.WIREGUARD | ProtocolType.AMNEZIA_WIREGUARD:
                peers_str += "[Wireguard] " if peer.peer_type == ProtocolType.WIREGUARD else "[Amnezia WG] "
                peers_str += f"{peer.peer_name or peer.shared_ips}: {PeerStatusChoices.to_string(peer.peer_status)} ({peer.shared_ips}) "
            case ProtocolType.XRAY:
                peers_str += f"[XRay] {peer.peer_name or peer.flow}: {PeerStatusChoices.to_string(peer.peer_status)} "
        if peer.peer_status == PeerStatusChoices.STATUS_CONNECTED:
            timer = datetime.datetime.strftime(peer.peer_timer, "%H:%M")
            peers_str += f"(активен до {timer})"
        peers_str += "\n"

    if client.userdata.expire_time:
        expire_time = f'До: {client.userdata.expire_time.strftime("%d.%m.%Y")}\n' + \
                      f'Осталось времени: {humanize.naturaldelta(client.userdata.expire_time - datetime.datetime.now())}'
    else:
        expire_time = "❌ Не оплачено"

    return [f"""ℹ️ <b>Информация об аккаунте</b>:
<b>ID</b>: <code>{client.userdata.user_id}</code>
📅 <b>Дата регистрации</b>: {client.userdata.registered_at.strftime("%d.%m.%Y в %H:%M")}
""",
f"""<b>Текущий статус</b>: {ClientStatusChoices.to_string(client.userdata.status)}
🕓 <b>Статус оплаты</b>:
<blockquote>{expire_time}</blockquote>

🛜 <b>Пиры</b>:
{peers_str or '❌ Нет пиров\n'}
"""]

def extend_users_usage_time(client: Client, time_to_add: datetime.timedelta) -> bool:
    now = datetime.datetime.now()

    if not isinstance(client.userdata.expire_time, datetime.datetime) or client.userdata.expire_time < now:
        client.userdata.expire_time = now

    client.set_expire_time(client.userdata.expire_time + time_to_add)

    if xray_peers := client.get_xray_peers():
        for peer in xray_peers:
            xray_worker.update_peer(peer, expiry_time=client.userdata.expire_time)

    return True

@bot_logger.catch()
def unblock_timeout_connections(client: Client) -> bool:
    peers = client.get_all_peers(serialized=True)
    for peer in peers:
        match peer.peer_status:
            case PeerStatusChoices.STATUS_TIME_EXPIRED:
                if peer.peer_type in [ProtocolType.WIREGUARD, ProtocolType.AMNEZIA_WIREGUARD]:
                    peer: WireguardPeer
                    wghub.enable_peer(peer)
                elif peer.peer_type == ProtocolType.XRAY:
                    peer: XrayPeer
                    xray_worker.enable_peer(peer)
                client.set_peer_status(peer.peer_id, PeerStatusChoices.STATUS_DISCONNECTED)
                client.set_status(ClientStatusChoices.STATUS_DISCONNECTED)
            case PeerStatusChoices.STATUS_CONNECTED:
                new_time = datetime.datetime.now() + datetime.timedelta(hours=core_cfg.peer_active_time)
                client.set_peer_timer(peer.peer_id, time=new_time)

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
        filename=f"{peer.peer_name or peer.peer_id}.conf"
    )

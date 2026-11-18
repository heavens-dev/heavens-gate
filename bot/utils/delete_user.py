"""Helpers for the ``/delete_user`` admin flow.

This module intentionally does not import `config.loader`: the composition root
runs at import time, which would make these helpers untestable from `tests/core`.
Dependencies of `purge_client` are passed in by the handler instead.
"""
from typing import Union

from core.db.db_works import Client, ClientFactory
from core.db.enums import ProtocolType, SubscriptionType
from core.utils.ip_utils import IPQueue
from core.watchdog.events import ConnectionEvents
from core.wg.wg_work import WGHub
from core.xray.xray_worker import XrayWorker


def delete_preview_text(client: Client, *, warning: bool = False) -> str:
    """Builds the identification message for the deletion confirmation.

    Args:
        client (Client): The client that is about to be deleted.
        warning (bool): Whether to add the second-step warning about an active subscription.

    Returns:
        str: HTML-formatted text for the preview message.
    """
    user = client.userdata
    expiry = user.subscription_expiry.strftime("%d.%m.%Y") if user.subscription_expiry else "нет"
    subscription = SubscriptionType.to_string(user.subscription_type) if user.subscription_type else "нет"

    text = (
        "🗑 <b>Удаление пользователя</b>\n"
        f"Имя: <b>{user.name}</b>\n"
        f"ID: <code>{user.user_id}</code>\n"
        f"Подписка: {subscription}, до {expiry}\n"
    )

    if org := client.is_org_member():
        text += f"Организация: <code>{org.name}</code> (ID: {org.org_id})\n"

    if owned_org := client.get_owned_org():
        text += (
            f"\n⚠️ Пользователь — владелец организации <code>{owned_org.orgdata.name}</code> "
            f"(ID: {owned_org.orgdata.org_id}). После удаления организация останется без владельца.\n"
        )

    if warning:
        text += (
            "\n⚠️ <b>Ты АБСОЛЮТНО ТОЧНО УВЕРЕН, что хочешь удалить пользователя "
            "с активной подпиской?</b>"
        )

    return text


async def purge_client(
    client: Client,
    *,
    wghub: WGHub,
    xray_worker: XrayWorker,
    ip_queue: IPQueue,
    connections_observer: ConnectionEvents
) -> bool:
    """Removes the client from every external system and then from the database.

    Args:
        client (Client): The client to purge.
        wghub (WGHub): WireGuard/AmneziaWG hub.
        xray_worker (XrayWorker): XRay worker.
        ip_queue (IPQueue): Pool of IP addresses to release.
        connections_observer (ConnectionEvents): Connection observer that tracks the client.

    Returns:
        bool: True if the client was deleted, False otherwise.
    """
    if xray_worker.remnawave and not xray_worker.remnawave_delete_user(client.userdata):
        return False

    for peer in client.get_all_peers(protocol_specific=True):
        if peer.type in (ProtocolType.WIREGUARD, ProtocolType.AMNEZIA_WIREGUARD):
            wghub.delete_peer(peer)
            ip_queue.release_ip(peer.shared_ips)

    for peer in client.get_xray_peers():
        xray_worker.delete_peer(peer)

    await connections_observer.remove_client(client.userdata.user_id)

    return bool(ClientFactory.delete_client_by_id(client.userdata.user_id))


def is_bot_admin(user_id: Union[int, str], admins: list[int]) -> bool:
    """Checks whether the user is a bot administrator.

    Args:
        user_id (Union[int, str]): Telegram ID of the user.
        admins (list[int]): IDs of bot administrators from the config.

    Returns:
        bool: True if the user must not be deleted, False otherwise.
    """
    return str(user_id) in {str(admin_id) for admin_id in admins}

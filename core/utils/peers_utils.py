from typing import Optional, Union

from core.db.db_works import Client
from core.db.enums import PeerStatusChoices, ProtocolType
from core.db.model_serializer import WireguardPeer, XrayPeer
from core.logs import core_logger
from core.wg.wg_work import WGHub
from core.xray.xray_worker import XrayWorker


def enable_peers(
        wghub: WGHub,
        xray_worker: XrayWorker,
        peers: list[Union[WireguardPeer, XrayPeer]],
        client: Client
    ) -> None:
    for peer in peers:
        match peer.peer_type:
            case ProtocolType.WIREGUARD | ProtocolType.AMNEZIA_WIREGUARD:
                wghub.enable_peer(peer)
            case ProtocolType.XRAY:
                xray_worker.enable_peer(peer, expire_time=client.userdata.expire_time)
            case _:
                core_logger.warning(f"Unknown peer type: {peer.peer_type}. Can't enable peer.")

        client.set_peer_status(peer.peer_id, PeerStatusChoices.STATUS_DISCONNECTED)

def disable_peers(
        wghub: WGHub,
        xray_worker: XrayWorker,
        peers: list[Union[WireguardPeer, XrayPeer]],
        client: Client = None
    ) -> None:
    for peer in peers:
        match peer.peer_type:
            case ProtocolType.WIREGUARD | ProtocolType.AMNEZIA_WIREGUARD:
                wghub.disable_peer(peer)
            case ProtocolType.XRAY:
                xray_worker.disable_peer(peer, expire_time=client.userdata.expire_time)
            case _:
                core_logger.warning(f"Unknown peer type: {peer.peer_type}. Can't disable peer.")

        client.set_peer_status(peer.peer_id, PeerStatusChoices.STATUS_BLOCKED)

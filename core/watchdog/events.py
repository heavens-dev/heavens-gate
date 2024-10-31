import asyncio
import datetime

from icmplib import async_ping

from core.db.db_works import Client, ClientFactory
from core.db.enums import ClientStatusChoices, PeerStatusChoices
from core.db.model_serializer import ConnectionPeer
from core.logs import core_logger
from core.watchdog.observer import EventObserver
from core.wg.wg_work import WGHub


class ConnectionEvents:
    def __init__(self,
                 wghub: WGHub,
                 listen_timer: int = 120,
                 connected_only_listen_timer: int = 60,
                 update_timer: int = 360,
                 active_hours: int = 5):
        self.listen_timer = listen_timer
        self.update_timer = update_timer
        self.connected_only_listen_timer = connected_only_listen_timer
        self.active_hours = active_hours
        self.wghub = wghub

        self.connected = EventObserver(required_types=[Client, ConnectionPeer])
        """Decorated methods must have a `Client` and `ConnectionPeer` argument"""
        self.disconnected = EventObserver(required_types=[Client, ConnectionPeer])
        """Decorated methods must have a `Client` and `ConnectionPeer` argument"""
        self.timer_observer = EventObserver(required_types=[Client, ConnectionPeer, bool])
        """Decorated methods must have a `Client`, `ConnectionPeer` and boolean argument.
        Boolean argument describes whether the trigger is a warning (**False**) or a disconnect (**True**)"""
        self.startup = EventObserver()

        self.clients: list[tuple[Client, list[ConnectionPeer]]] = [
            (client, client.get_peers()) for client in ClientFactory.select_clients()
        ]
        """List of all `Client`s and their `ConnectionPeer`s"""

        self.__clients_lock = asyncio.Lock()
        """Internal lock that prevents updating `self.clients`
        during client connection checks"""

    async def __check_connection(self, client: Client, peer: ConnectionPeer, warn: bool = False) -> bool:
        if isinstance(peer.peer_timer, datetime.datetime) and peer.peer_status == PeerStatusChoices.STATUS_CONNECTED:
            timedelta = peer.peer_timer - datetime.datetime.now()

            if timedelta <= datetime.timedelta(minutes=2):
                # True is disable
                await self.timer_observer.trigger(client, peer, True)
                await self.emit_timeout_disconnect(client, peer)
                return False
            elif timedelta <= datetime.timedelta(minutes=15) and warn:
                # False is warning
                await self.timer_observer.trigger(client, peer, False)

        host = await async_ping(peer.shared_ips)

        if host.is_alive:
            if peer.peer_status == PeerStatusChoices.STATUS_DISCONNECTED:
                await self.emit_connect(client, peer)
            return True

        if peer.peer_status == PeerStatusChoices.STATUS_CONNECTED:
            await self.emit_disconnect(client, peer)
        return False

    async def __listen_clients(self, listen_timer: int, connected_only: bool = False):
        while True:
            # looks cringy, but idk how to make it prettier
            async with self.__clients_lock:
                async with asyncio.TaskGroup() as group:
                    for client, peers in self.clients:
                        for peer in peers:
                            if peer.peer_status in [
                                PeerStatusChoices.STATUS_TIME_EXPIRED,
                                PeerStatusChoices.STATUS_BLOCKED
                                ]:
                                continue

                            if connected_only:
                                if peer.peer_status == PeerStatusChoices.STATUS_CONNECTED:
                                    group.create_task(
                                        self.__check_connection(client, peer)
                                    )
                                continue
                            group.create_task(
                                self.__check_connection(client, peer, True)
                            )

            with core_logger.contextualize(connected_only=connected_only):
                core_logger.debug(f"Done listening for connections. Sleeping for {listen_timer} sec")
            await asyncio.sleep(listen_timer)

    async def emit_connect(self, client: Client, peer: ConnectionPeer):
        """Propagates connection event to handlers.
        Sets the time until which the connection can be active.

        Updates Client status to `ClientStatusChoices.STATUS_CONNECTED`
        and Peer status to `PeerStatusChoices.STATUS_DISCONNECTED`"""
        new_time = datetime.datetime.now() + datetime.timedelta(hours=self.active_hours)
        client.set_peer_timer(peer.id, new_time)
        client.set_peer_status(peer.id, PeerStatusChoices.STATUS_CONNECTED)
        client.set_status(ClientStatusChoices.STATUS_CONNECTED)
        await self.connected.trigger(client, peer)

    async def emit_disconnect(self, client: Client, peer: ConnectionPeer):
        """Propagates disconnect event to handlers.

        Updates Client status to `ClientStatusChoices.STATUS_DISCONNECTED`
        and Peer status to `PeerStatusChoices.STATUS_DISCONNECTED`"""
        client.set_peer_status(peer.id, PeerStatusChoices.STATUS_DISCONNECTED)
        if len(client.get_connected_peers()) == 0:
            client.set_status(ClientStatusChoices.STATUS_DISCONNECTED)
        await self.disconnected.trigger(client, peer)

    async def emit_timeout_disconnect(self, client: Client, peer: ConnectionPeer):
        client.set_peer_status(peer.id, PeerStatusChoices.STATUS_TIME_EXPIRED)
        # avoid triggering the timer_observer multiple times
        peer.peer_status = PeerStatusChoices.STATUS_TIME_EXPIRED
        self.wghub.disable_peer(peer)
        if len(client.get_connected_peers()) == 0:
            client.set_status(ClientStatusChoices.STATUS_TIME_EXPIRED)
        await self.disconnected.trigger(client, peer)

    async def __update_clients_list(self):
        while True:
            async with self.__clients_lock:
                self.clients = [
                    (client, client.get_peers()) for client in ClientFactory.select_clients()
                ]
                core_logger.debug(f"Done updating clients list. Sleeping for {self.update_timer} sec")

            await asyncio.sleep(self.update_timer)

    async def listen_events(self):
        await self.startup.trigger()
        async with asyncio.TaskGroup() as group:
            group.create_task(self.__update_clients_list())
            group.create_task(self.__listen_clients(self.listen_timer))
            group.create_task(
                self.__listen_clients(
                    self.connected_only_listen_timer,
                    connected_only=True
                )
            )

    def listen_events_runner(self):
        return asyncio.run(self.listen_events())

import asyncio
import datetime
from contextlib import suppress
from typing import Callable, Coroutine, Union

from icmplib import async_ping

from core.db.db_works import Client, ClientFactory
from core.db.enums import ClientStatusChoices, PeerStatusChoices, ProtocolType
from core.db.model_serializer import BasePeer, WireguardPeer, XrayPeer
from core.logs import core_logger
from core.utils.peers_utils import disable_peers
from core.watchdog.object import CallableObject
from core.watchdog.observer import EventObserver
from core.wg.wg_work import WGHub
from core.xray.xray_worker import XrayWorker


class ConnectionEvents:
    def __init__(self,
                 wghub: WGHub,
                 xray: XrayWorker,
                 listen_timer: int = 120,
                 connected_only_listen_timer: int = 60,
                 update_timer: int = 360,
                 active_hours: int = 5):
        self.listen_timer = listen_timer
        self.update_timer = update_timer
        self.connected_only_listen_timer = connected_only_listen_timer
        self.active_hours = active_hours
        self.wghub = wghub
        self.xray = xray

        self.connected = EventObserver(required_types=[Client, BasePeer])
        """Decorated methods must have a `Client` and `ConnectionPeer` argument"""
        self.disconnected = EventObserver(required_types=[Client, BasePeer])
        """Decorated methods must have a `Client` and `ConnectionPeer` argument"""
        # TODO: separate timer_observer into two different observers for warning and disconnect
        self.timer_observer = EventObserver(required_types=[Client, BasePeer, bool])
        """Decorated methods must have a `Client`, `ConnectionPeer` and `disconnect` boolean argument.
        `disconnect` describes whether the trigger is a warning (**False**) or a disconnect (**True**)"""
        self.startup = EventObserver()

        self.clients: list[tuple[Client, list[Union[WireguardPeer, XrayPeer]]]] = [
            (client, client.get_all_peers(serialized=True)) for client in ClientFactory.select_clients()
        ]
        """List of all `Client`s and their `ConnectionPeer`s"""

        self.__clients_lock = asyncio.Lock()
        """Internal lock that prevents updating `self.clients`
        during client connection checks"""

    async def __check_connection(self, client: Client, peer: BasePeer, warn: bool = False) -> bool:
        if isinstance(peer.peer_timer, datetime.datetime) and peer.peer_status == PeerStatusChoices.STATUS_CONNECTED:
            timedelta = peer.peer_timer - datetime.datetime.now()

            if timedelta <= datetime.timedelta(0):
                # True is disable
                await self.timer_observer.trigger(client, peer, disconnect=True)
                await self.emit_timeout_disconnect(client, peer)
                return False
            elif timedelta <= datetime.timedelta(minutes=15) and warn:
                # False is warning
                await self.timer_observer.trigger(client, peer, disconnect=False)

        if peer.peer_type in (ProtocolType.WIREGUARD, ProtocolType.AMNEZIA_WIREGUARD):
            host = await async_ping(peer.shared_ips)
            if host.is_alive:
                if peer.peer_status == PeerStatusChoices.STATUS_DISCONNECTED:
                    await self.emit_connect(client, peer)
                return True

            if peer.peer_status == PeerStatusChoices.STATUS_CONNECTED:
                await self.emit_disconnect(client, peer)
            return False
        elif peer.peer_type == ProtocolType.XRAY:
            if self.xray.is_connected(peer):
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
                        if client.userdata.status in [
                            ClientStatusChoices.STATUS_ACCOUNT_BLOCKED,
                            ClientStatusChoices.STATUS_TIME_EXPIRED]:
                            continue

                        for peer in peers:
                            if peer.peer_status in [
                                PeerStatusChoices.STATUS_TIME_EXPIRED,
                                PeerStatusChoices.STATUS_BLOCKED]:
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

    async def emit_connect(self, client: Client, peer: BasePeer):
        """Propagates connection event to handlers.
        Sets the time until which the connection can be active.

        Updates Client status to `ClientStatusChoices.STATUS_CONNECTED`
        and Peer status to `PeerStatusChoices.STATUS_DISCONNECTED`"""
        new_time = datetime.datetime.now() + datetime.timedelta(hours=self.active_hours)
        client.set_peer_timer(peer.peer_id, new_time)
        client.set_peer_status(peer.peer_id, PeerStatusChoices.STATUS_CONNECTED)
        client.set_status(ClientStatusChoices.STATUS_CONNECTED)
        # avoid triggering connection event multiple times
        peer.peer_status = PeerStatusChoices.STATUS_CONNECTED
        peer.peer_timer = new_time
        await self.connected.trigger(client, peer)

    # TODO: update typehint for peer
    async def emit_disconnect(self, client: Client, peer: WireguardPeer):
        """Propagates disconnect event to handlers.

        Updates Client status to `ClientStatusChoices.STATUS_DISCONNECTED`
        and Peer status to `PeerStatusChoices.STATUS_DISCONNECTED`"""
        client.set_peer_status(peer.peer_id, PeerStatusChoices.STATUS_DISCONNECTED)
        # avoid triggering disconnection event multiple times
        peer.peer_status = PeerStatusChoices.STATUS_DISCONNECTED
        if len(client.get_connected_peers()) == 0:
            client.set_status(ClientStatusChoices.STATUS_DISCONNECTED)
        await self.disconnected.trigger(client, peer)

    # TODO: update typehint for peer
    async def emit_timeout_disconnect(self, client: Client, peer: WireguardPeer):
        client.set_peer_status(peer.peer_id, PeerStatusChoices.STATUS_TIME_EXPIRED)
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
                    (client, client.get_all_peers(serialized=True)) for client in ClientFactory.select_clients()
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


class IntervalEvents:
    def __init__(self, wg_hub: WGHub, xray: XrayWorker):
        self.expire_date_warning_observer = EventObserver(required_types=[Client])
        """Observer triggers if there's one day left before blocking user. Requires `Client` as an argument."""
        self.expire_date_block_observer = EventObserver(required_types=[Client])
        """Observer triggers if the expiration date has passed. Requires `Client` as an argument."""
        self.wg_hub = wg_hub
        self.xray = xray

    async def interval_runner(self, func: Union[CallableObject, Callable, Coroutine], interval: datetime.timedelta, *args, **kwargs):
        """
        Periodically executes a given function at specified intervals.
        Args:
            func (Union[CallableObject, Callable, Coroutine]): Function or coroutine to be executed periodically.
            interval (datetime.timedelta): Time interval between each execution.
        Example:
            >>> async def my_task():
            ...    print("Task executed")
            >>> await interval_runner(my_task, datetime.timedelta(seconds=10))
        """
        if not isinstance(func, CallableObject):
            func = CallableObject(callback=func)

        while True:
            await func.call(*args, **kwargs)
            core_logger.info(f"Interval check for job {func.callback.__name__} done. Sleeping for {interval}.")
            await asyncio.sleep(interval.total_seconds())

    async def scheduled_runner(self,
                              func: Union[CallableObject, Callable, Coroutine],
                              run_at: datetime.time,
                              *args, **kwargs):
        """
        Asynchronously runs a scheduled function at a specified time every day.
        Args:
            func (Union[CallableObject, Callable, Coroutine]): The function or coroutine to be scheduled.
            run_at (datetime.time): The time at which the function should run each day.
        Raises:
            TypeError: If `func` is not an instance of CallableObject, Callable, or Coroutine.
        """
        if not isinstance(func, CallableObject):
            func = CallableObject(callback=func)

        while True:
            now = datetime.datetime.now()
            next_run = datetime.datetime.combine(datetime.date.today(), run_at)

            if next_run < now:
                next_run += datetime.timedelta(days=1)

            core_logger.info(f"Scheduled job {func.callback.__name__}. Next run at {next_run}.")
            await asyncio.sleep((next_run - now).total_seconds())
            await func.call(*args, **kwargs)
            core_logger.info(f"Job {func.callback.__name__} done.")

    async def __check_users_expire_date(self):
        now = datetime.datetime.now()
        for client in ClientFactory.select_clients():
            if not isinstance(client.userdata.expire_time, datetime.datetime) or \
               client.userdata.status == ClientStatusChoices.STATUS_ACCOUNT_BLOCKED:
                continue

            if client.userdata.expire_time.date() <= now.date():
                core_logger.info(f"Blocking user {client.userdata.name} due to expired account.")
                client.set_status(ClientStatusChoices.STATUS_ACCOUNT_BLOCKED)
                peers = client.get_all_peers(serialized=True)
                disable_peers(self.wg_hub, self.xray, peers, client=client)
                await self.expire_date_block_observer.trigger(client)
            elif (client.userdata.expire_time - datetime.timedelta(days=1)).date() <= now.date():
                core_logger.info(f"Warning user {client.userdata.name} about the expiration date.")
                await self.expire_date_warning_observer.trigger(client)

    async def run_checkers(self):
        async with asyncio.TaskGroup() as group:
            group.create_task(self.scheduled_runner(self.__check_users_expire_date, datetime.time(3, 0)))

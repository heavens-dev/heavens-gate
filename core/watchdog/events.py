import asyncio
from core.db.model_serializer import ConnectionPeer
from core.watchdog.observer import EventObserver
from core.db.db_works import Client, ClientFactory
from icmplib import async_ping
from core.db.enums import StatusChoices


class ConnectionEvents:
    def __init__(self, listen_timer: int = 60, update_timer: int = 360):
        self.listen_timer = listen_timer
        self.update_timer = update_timer

        self.connected = EventObserver()
        self.disconnected = EventObserver()
        self.startup = EventObserver()

        self.clients: list[tuple[Client, list[ConnectionPeer]]] = [
            (client, client.get_peers()) for client in ClientFactory.select_clients()
        ]
        """List of all `Client`s and their `ConnectionPeer`s"""

        self.connected_clients: list[Client] = []

    async def __check_connection(self, client: Client, peer: ConnectionPeer) -> bool:
        host = await async_ping(peer.shared_ips)

        if host.is_alive:
            if client not in self.connected_clients:
                await self.emit_connect(client)
            return True

        if client in self.connected_clients:
            await self.emit_disconnect(client)
        return False

    async def __listen_connected(self):
        while True:
            async with asyncio.TaskGroup() as group:
                for client, peers in self.clients:
                    for peer in peers:
                        group.create_task(
                            self.__check_connection(client, peer)
                        )

            print(f"Done listening connections. Sleeping for {self.listen_timer} sec")
            await asyncio.sleep(self.listen_timer)

    async def emit_connect(self, client: Client):
        """Appends connected clients and propagates connection event to handlers.

        Updates Client status to `StatusChoices.STATUS_CONNECTED`"""
        client.set_status(StatusChoices.STATUS_CONNECTED)
        self.connected_clients.append(client)
        await self.connected.trigger(client)

    async def emit_disconnect(self, client: Client):
        """Removes client from `connected_clients` and propagates disconnect event to handlers.

        Updates Client status to `StatusChoices.STATUS_DISCONNECTED`"""
        client.set_status(StatusChoices.STATUS_DISCONNECTED)
        self.connected_clients.remove(client)
        await self.disconnected.trigger(client)

    async def __update_clients_list(self):
        while True:
            self.clients = [
                (client, client.get_peers()) for client in ClientFactory.select_clients()
            ]
            print(f"Done updating clients list. Sleeping for {self.update_timer} sec")
            await asyncio.sleep(self.update_timer)

    async def listen_events(self):
        await self.startup.trigger()
        async with asyncio.TaskGroup() as group:
            group.create_task(self.__update_clients_list())
            group.create_task(self.__listen_connected())

    def listen_events_runner(self):
        return asyncio.run(self.listen_events())

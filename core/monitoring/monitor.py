import asyncio

from prometheus_client import start_http_server

from core.db.enums import ClientStatusChoices, PeerStatusChoices, ProtocolType
from core.logs import core_logger
from core.monitoring.metrics import (AMNEZIA_PEERS, CLIENTS_BY_STATUS,
                                     CONNECTED_CLIENTS, CONNECTED_PEERS,
                                     CONNECTED_PEERS_BY_PROTOCOL,
                                     PEERS_BY_STATUS, SERVER_UP, TOTAL_CLIENTS,
                                     TOTAL_PEERS, WIREGUARD_PEERS, XRAY_PEERS)
from core.watchdog.events import ConnectionEvents


class PrometheusMonitor:
    def __init__(self, port: int = 9090):
        self.port = port
        self.__server_started = False
        self.__server_thread = None
        self.__server_wsgi = None

    def start_server(self):
        """Запускает HTTP-сервер для Prometheus"""
        if not self.__server_started:
            self.__server_wsgi, self.__server_thread = start_http_server(self.port)
            self.__server_started = True
            core_logger.info(f"Prometheus metrics server started on port {self.port}")
        else:
            core_logger.warning("Tried to start Prometheus server, but it's already running.")

    def stop_server(self):
        if self.__server_started:
            self.__server_wsgi.shutdown()
            self.__server_wsgi.server_close()
            self.__server_thread.join()
            self.__server_started = False
            core_logger.info("Prometheus metrics server stopped")
        else:
            core_logger.warning("Tried to stop Prometheus server, but it wasn't running.")

    @staticmethod
    async def update_metrics_task(connection_events: ConnectionEvents, interval: int = 60):
        """Задача для периодического обновления метрик"""
        while True:
            try:
                CLIENTS_BY_STATUS.clear()
                # Обновление метрик клиентов и пиров
                total_clients = len(connection_events.clients)
                TOTAL_CLIENTS.set(total_clients)

                connected_clients = sum(1 for client, _ in connection_events.clients
                                       if client.userdata.status == ClientStatusChoices.STATUS_CONNECTED)
                CONNECTED_CLIENTS.set(connected_clients)

                # Обновление метрик по статусам
                status_counts = {}

                protocol_counts = {protocol.name.lower(): 0 for protocol in ProtocolType}
                total_peers = 0
                connected_peers = 0

                for client, peers in connection_events.clients:
                    CLIENTS_BY_STATUS.labels(status=client.userdata.status.name).inc()

                    for peer in peers:
                        total_peers += 1
                        if peer.peer_status == PeerStatusChoices.STATUS_CONNECTED:
                            connected_peers += 1
                            CONNECTED_PEERS_BY_PROTOCOL.labels(protocol=peer.peer_type.name.lower()).inc()

                        protocol_counts[peer.peer_type.name.lower()] += 1

                        # Обновление статусов пиров
                        peer_status = peer.peer_status
                        if peer_status not in status_counts:
                            status_counts[peer_status] = 0
                        status_counts[peer_status] += 1

                # Установка значений метрик
                TOTAL_PEERS.set(total_peers)
                CONNECTED_PEERS.set(connected_peers)
                WIREGUARD_PEERS.set(protocol_counts[ProtocolType.WIREGUARD.name.lower()])
                AMNEZIA_PEERS.set(protocol_counts[ProtocolType.AMNEZIA_WIREGUARD.name.lower()])
                XRAY_PEERS.set(protocol_counts[ProtocolType.XRAY.name.lower()])

                for status, count in status_counts.items():
                    PEERS_BY_STATUS.labels(status=status).set(count)

                # Проверка доступности серверов
                SERVER_UP.set(1)  # 1 - доступен, 0 - недоступен

                core_logger.debug("Prometheus metrics updated")
            except Exception as e:
                core_logger.exception(f"Error updating metrics: {e}")

            await asyncio.sleep(interval)

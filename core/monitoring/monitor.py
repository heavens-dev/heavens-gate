import asyncio
import base64
import threading
import time
from wsgiref.simple_server import make_server

from prometheus_client import make_wsgi_app

from core.db.enums import ClientStatusChoices, PeerStatusChoices, ProtocolType
from core.logs import core_logger
from core.monitoring.metrics import (AMNEZIA_PEERS, CLIENTS_BY_STATUS,
                                     CONNECTED_CLIENTS, CONNECTED_PEERS,
                                     CONNECTED_PEERS_BY_PROTOCOL,
                                     PEERS_BY_STATUS, TOTAL_CLIENTS,
                                     TOTAL_PEERS, UPTIME_SECONDS,
                                     WIREGUARD_PEERS, XRAY_PEERS)
from core.watchdog.events import ConnectionEvents


class PrometheusMonitor:
    def __init__(self, port: int = 9090, username: str = None, password: str = None):
        self.port = port
        self.uptime_start = time.time()
        self.__username = username
        self.__password = password
        self.__server_started = False
        self.__server_thread = None
        self.__server_wsgi = None

    def _create_auth_middleware(self, app):
        def auth_middleware(environ, start_response):
            if not self.__username or not self.__password:
                return app(environ, start_response)

            auth_header = environ.get('HTTP_AUTHORIZATION')
            if auth_header:
                auth_type, auth_data = auth_header.split(' ', 1)
                if auth_type.lower() == 'basic':
                    try:
                        auth_decoded = base64.b64decode(auth_data).decode('utf-8')
                        provided_username, provided_password = auth_decoded.split(':', 1)
                        if provided_username == self.__username and provided_password == self.__password:
                            return app(environ, start_response)
                    except Exception as e:
                        core_logger.exception(f"Authentication error: {e}")

            start_response('401 Unauthorized', [
                ('WWW-Authenticate', 'Basic realm="Prometheus Metrics"'),
                ('Content-Type', 'text/plain')
            ])
            return [b'Unauthorized']

        return auth_middleware

    def start_server(self):
        """Запускает HTTP-сервер для Prometheus"""
        if not self.__server_started:
            metrics_app = make_wsgi_app()

            if self.__username and self.__password:
                auth_app = self._create_auth_middleware(metrics_app)
                core_logger.info("Prometheus metrics server will use Basic Authentication.")
            else:
                auth_app = metrics_app
                core_logger.info("Prometheus metrics server will NOT use authentication.")

            self.__server_wsgi = make_server('0.0.0.0', self.port, auth_app)
            self.__server_thread = threading.Thread(target=self.__server_wsgi.serve_forever)
            self.__server_thread.daemon = True
            self.__server_thread.start()

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

    async def update_metrics_task(self, connection_events: ConnectionEvents, interval: int = 60):
        """Задача для периодического обновления метрик"""
        while True:
            try:
                CLIENTS_BY_STATUS.clear()
                CONNECTED_PEERS_BY_PROTOCOL.clear()
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

                UPTIME_SECONDS.set(time.time() - self.uptime_start)

                core_logger.debug("Prometheus metrics updated")
            except Exception as e:
                core_logger.exception(f"Error updating metrics: {e}")

            await asyncio.sleep(interval)

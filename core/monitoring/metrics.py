from prometheus_client import Counter, Gauge

# Основные метрики
CONNECTED_CLIENTS = Gauge('hg_connected_clients', 'Number of connected clients')
TOTAL_CLIENTS = Gauge('hg_total_clients', 'Total number of clients')
CONNECTED_PEERS = Gauge('hg_connected_peers', 'Number of connected peers')
TOTAL_PEERS = Gauge('hg_total_peers', 'Total number of peers')

# Метрики по типам протоколов
WIREGUARD_PEERS = Gauge('hg_wireguard_peers', 'Number of WireGuard peers')
AMNEZIA_PEERS = Gauge('hg_amnezia_peers', 'Number of Amnezia peers')
XRAY_PEERS = Gauge('hg_xray_peers', 'Number of XRay peers')

# Метрики событий
CONNECT_EVENTS = Counter('hg_connect_events', 'Number of connect events')
DISCONNECT_EVENTS = Counter('hg_disconnect_events', 'Number of disconnect events')
TIMEOUT_EVENTS = Counter('hg_timeout_events', 'Number of timeout events')

# Метрики статусов
PEERS_BY_STATUS = Gauge('hg_peers_by_status', 'Number of peers by status', ['status'])
CLIENTS_BY_STATUS = Gauge('hg_clients_by_status', 'Number of clients by status', ['status'])
CONNECTED_PEERS_BY_PROTOCOL = Gauge('hg_connected_peers_by_protocol', 'Number of connected peers by protocol', ['protocol'])

UPTIME_SECONDS = Gauge('hg_uptime_seconds', 'Uptime of the monitoring and main service in seconds')

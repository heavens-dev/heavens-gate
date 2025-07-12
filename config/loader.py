import humanize.i18n
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config.settings import Config
from core.db.db_works import ClientFactory
from core.db.models import init_db
from core.logs import core_logger, init_file_loggers
from core.utils.ip_utils import IPQueue, generate_ip_addresses
from core.watchdog.events import ConnectionEvents, IntervalEvents
from core.wg.wg_work import WGHub
from core.xray.xray_worker import XrayWorker

PATH_TO_CONFIG = "config.conf"

humanize.i18n.activate("ru_RU")

cfg = Config(PATH_TO_CONFIG)
db_cfg = cfg.get_database_config()
bot_cfg = cfg.get_bot_config()
wireguard_server_config = cfg.get_wireguard_server_config()
core_cfg = cfg.get_core_config()
xray_cfg = cfg.get_xray_server_config()

if cfg.debug:
    core_logger.warning("DEBUG MODE IS ENABLED! Disable it in production! Every message will be logged.")
if cfg.is_canary:
    core_logger.warning("Canary version is enabled! Disable it on production.")

init_file_loggers(core_cfg.logs_path, is_debug=cfg.debug)

RESERVED_IP_ADDRESSES = [
    wireguard_server_config.user_ip + ".0",
    wireguard_server_config.user_ip + ".1",
    wireguard_server_config.user_ip + ".255"
]

bot_instance = Bot(
    token=bot_cfg.token,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
bot_dispatcher = Dispatcher(storage=MemoryStorage())

db_instance = init_db(db_cfg.path)

_all_ips = generate_ip_addresses(wireguard_server_config.user_ip, mask="24")
ip_queue = IPQueue([ip for ip in _all_ips
                    if ip not in ClientFactory.get_used_ip_addresses()
                    and ip not in RESERVED_IP_ADDRESSES])
core_logger.debug(f"Number of available ip addresses: {ip_queue.count_available_addresses()}")

wghub = WGHub(wireguard_server_config.path)
xray_worker = XrayWorker(
    xray_cfg.host,
    xray_cfg.port,
    xray_cfg.web_path,
    xray_cfg.username,
    xray_cfg.password,
    xray_cfg.token,
    xray_cfg.tls
)

try:
    inbound = xray_worker.api.inbound.get_by_id(xray_cfg.inbound_id)
    with core_logger.contextualize(
        remark=inbound.remark,
        is_enabled=inbound.enable,
        protocol=inbound.protocol,
    ):
        core_logger.info(f"Successfully fetched inbound with ID {xray_cfg.inbound_id}.")
except ValueError:
    core_logger.exception(f"Couldn't fetch XRay inbound with ID {xray_cfg.inbound_id}!")

connections_observer = ConnectionEvents(
    wghub,
    xray_worker,
    listen_timer=core_cfg.connection_listen_timer,
    update_timer=core_cfg.connection_update_timer,
    connected_only_listen_timer=core_cfg.connection_connected_only_listen_timer,
    active_hours=core_cfg.peer_active_time
)

interval_observer = IntervalEvents(wghub, xray_worker)

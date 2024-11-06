from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config.settings import Config
from core.db.db_works import ClientFactory
from core.db.models import init_db
from core.logs import core_logger
from core.utils.ip_utils import IPQueue, generate_ip_addresses
from core.watchdog.events import ConnectionEvents
from core.wg.wg_work import WGHub

PATH_TO_CONFIG = "config.conf"

cfg = Config(PATH_TO_CONFIG)
db_cfg = cfg.get_database_config()
bot_cfg = cfg.get_bot_config()
server_cfg = cfg.get_server_config()
core_cfg = cfg.get_core_config()

RESERVED_IP_ADDRESSES = [server_cfg.user_ip + ".0", server_cfg.user_ip + ".1"]

bot_instance = Bot(
    token=bot_cfg.token,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
bot_dispatcher = Dispatcher(storage=MemoryStorage())

db_instance = init_db(db_cfg.path)

_all_ips = generate_ip_addresses(server_cfg.user_ip, mask="24")
ip_queue = IPQueue([ip for ip in _all_ips
                    if ip not in ClientFactory.get_ip_addresses()
                    and ip not in RESERVED_IP_ADDRESSES])
core_logger.debug(f"Number of available ip addresses: {ip_queue.count_available_addresses()}")

wghub = WGHub(server_cfg.path)

connections_observer = ConnectionEvents(
    wghub,
    listen_timer=30,
    update_timer=30,
    active_hours=core_cfg.peer_active_time
)

from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from core.watchdog.events import ConnectionEvents
from aiogram.enums import ParseMode
from aiogram import Bot, Dispatcher
from core.db.models import init_db
from config.settings import Config


path_to_config = "config.conf"

cfg = Config(path_to_config)

bot_cfg = cfg.get_bot_config()
bot_instance = Bot(
    token=bot_cfg.token,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
bot_dispatcher = Dispatcher(storage=MemoryStorage())

db_cfg = cfg.get_database_config()
db_instance = init_db(db_cfg.path)

server_cfg = cfg.get_server_config()

connections_observer = ConnectionEvents(listen_timer=30, update_timer=30)

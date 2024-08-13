from config.settings import Config
from core.db.models import init_db
from aiogram import Bot, Dispatcher, Router, F
from aiogram.fsm.storage.memory import MemoryStorage


path_to_config = "config.conf"

cfg = Config(path_to_config)

bot_cfg = cfg.get_bot_config()
bot_instance = Bot(token=bot_cfg.token)
bot_dispatcher = Dispatcher(storage=MemoryStorage())

admin_router = Router()
admin_router.message.filter(
    F.from_user.id.in_(bot_cfg.admins)
)

user_router = Router()

db_cfg = cfg.get_database_config()
db_instance = init_db(db_cfg.path)

server_cfg = cfg.get_server_config()

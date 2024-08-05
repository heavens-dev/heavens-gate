from config.settings import Config
from core.db.models import init_db


path_to_config = "config.conf"

cfg = Config("config.conf")

bot_cfg = cfg.get_bot_config()
db_cfg = cfg.get_database_config()

db = init_db(db_cfg.path)

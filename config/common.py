from config.settings import Config

path_to_config = "config.conf"

cfg = Config("config.conf")
bot_cfg = cfg.get_bot_config()

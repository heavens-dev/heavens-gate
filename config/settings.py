from configparser import ConfigParser
from typing import Type
import os


class Config:
    cfg: ConfigParser

    def __init__(self, path_to_config: str):
        if not os.path.exists(path_to_config):
            raise FileNotFoundError(f"File was not found on path {path_to_config}")
        self.path = path_to_config

        self.cfg = ConfigParser()
        self.cfg.read(path_to_config)

    def get_bot_config(self):
        return self.Bot(
            config_instance=self,
            token=self.cfg.get("TelegramBot", "token", fallback=None),
            admins=self.cfg.get("TelegramBot", "admins", fallback="")
        )
    
    def write_changes(self) -> bool:
        with open(self.path, "w", encoding="utf-8") as f:
            self.cfg.write(f)

        return True

    class Bot:
        def __init__(self, config_instance: Type["Config"], token: str, admins: str):
            self.token = token

            if not self.token:
                raise ValueError("Token MUST be specified in config file. For God's sake!")

            self.admins = [int(admin_id) for admin_id in admins.split(",")] if admins else []
            self.__config_instance = config_instance

        def add_admin(self, admin_id: int) -> bool:
            if admin_id in self.admins:
                return False
            self.admins.append(admin_id)
            self.__config_instance.cfg.set("TelegramBot", "admins", ",".join(str(i) for i in self.admins))
            self.__config_instance.write_changes()

            return True

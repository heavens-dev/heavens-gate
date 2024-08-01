from configparser import ConfigParser
import os


class Config:
    def __init__(self, path_to_config: str):
        if not os.path.exists(path_to_config):
            raise FileNotFoundError(f"File was not found on path {path_to_config}")

        self.cfg = ConfigParser()
        self.cfg.read(path_to_config)

        self.BotConfig = self.Bot(
            token=self.cfg.get("TelegramBot", "token", fallback=None)
        )

    class Bot:
        def __init__(self, token: str):
            self.token = token

            if not self.token:
                raise ValueError("Token MUST be specified in config file. For God's sake!")

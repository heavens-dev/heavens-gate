import os
import warnings
from configparser import ConfigParser
from typing import Optional, Type


class Config:
    cfg: ConfigParser

    def __init__(self, path_to_config: str):
        if not os.path.exists(path_to_config):
            raise FileNotFoundError(f"File was not found on path {path_to_config}")
        self.path = path_to_config

        self.cfg = ConfigParser(strict=False)
        self.cfg.read(path_to_config)

        self.debug = self.cfg.getboolean("core", "debug", fallback=False)
        self.is_canary = self.cfg.getboolean("core", "is_canary", fallback=False)

    def get_bot_config(self):
        return self.Bot(
            config_instance=self,
            token=self.cfg.get("TelegramBot", "token", fallback=None),
            admins=self.cfg.get("TelegramBot", "admins", fallback=""),
            faq_url=self.cfg.get("TelegramBot", "faq_url", fallback=None)
        )

    def get_database_config(self):
        return self.Database(
            path=self.cfg.get("db", "path", fallback="db.sqlite")
        )

    def get_wireguard_server_config(self, *args, **kwargs):
        return self.WireguardServer(
            path=self.cfg.get("WireguardServer", "Path", fallback=os.getcwd() + "/wg0.conf"),
            user_ip=self.cfg.get("WireguardServer", "IP", fallback="127.0.0"),
            user_ip_mask=self.cfg.get("WireguardServer", "IPMask", fallback=32),
            private_key=self.cfg.get("WireguardServer", "PrivateKey", fallback="@!ChAngEME!@"),
            public_key=self.cfg.get("WireguardServer", "PublicKey", fallback="@!ChAngEME!@"),
            endpoint_ip=self.cfg.get("WireguardServer", "EndpointIP", fallback="192.168.27.27"),
            endpoint_port=self.cfg.get("WireguardServer", "EndpointPort", fallback="10000"),
            dns_server=self.cfg.get("WireguardServer", "DNS", fallback="8.8.8.8"),
            junk=self.cfg.get("WireguardServer", "Junk", fallback=""),
            *args, **kwargs
        )

    def get_core_config(self):
        return self.Core(
            peer_active_time=self.cfg.getint("core", "peer_active_time", fallback=6),
            connection_listen_timer=self.cfg.getint("core", "connection_listen_timer", fallback=120),
            connection_update_timer=self.cfg.getint("core", "connection_update_timer", fallback=360),
            connection_connected_only_listen_timer=self.cfg.getint("core", "connection_connected_only_listen_timer", fallback=60),
            logs_path=self.cfg.get("core", "logs_path", fallback="./logs")
        )

    def get_xray_server_config(self):
        return self.XrayServer(
            host=self.cfg.get("Xray", "host"),
            port=self.cfg.get("Xray", "port"),
            web_path=self.cfg.get("Xray", "web_path"),
            username=self.cfg.get("Xray", "username"),
            password=self.cfg.get("Xray", "password"),
            token=self.cfg.get("Xray", "token", fallback=None),
            tls=self.cfg.getboolean("Xray", "tls", fallback=True),
            inbound_id=self.cfg.getint("Xray", "inbound_id", fallback=1)
        )

    def write_changes(self) -> bool:
        with open(self.path, "w", encoding="utf-8") as f:
            self.cfg.write(f)

        return True

    class Bot:
        def __init__(self, config_instance: Type["Config"], token: str, admins: str, faq_url: Optional[str]):
            if not token or token.lower() == "none":
                raise ValueError("Token MUST be specified in config file. For God's sake!")

            self.token = token
            self.faq_url = faq_url

            if self.faq_url and not self.faq_url.startswith("http"):
                warnings.warn("FAQ URL should start with http or https", UserWarning)
                self.faq_url = None
            elif not self.faq_url or self.faq_url.lower() == "none":
                self.faq_url = None

            self.__admins = [int(admin_id) for admin_id in admins.split(",")] if admins else []
            self.__config_instance = config_instance

        @property
        def admins(self) -> list[int]:
            """List of user ids that have special rights"""
            return self.__admins

        def add_admin(self, admin_id: int) -> bool:
            if admin_id in self.admins:
                return False
            self.__admins.append(admin_id)
            self.__config_instance.cfg.set("TelegramBot", "admins", ",".join(str(i) for i in self.admins))
            self.__config_instance.write_changes()

            return True

    class Database:
        def __init__(self, path: str):
            self.path = path

    class WireguardServer:
        def __init__(
                self,
                path: str,
                user_ip: str,
                user_ip_mask: str,
                private_key: str,
                public_key: str,
                endpoint_ip: str,
                endpoint_port: str,
                dns_server: str,
                junk: str,
                *args, **kwargs
            ):
            self.path = path
            self.user_ip = user_ip
            self.user_ip_mask = user_ip_mask
            self.private_key = private_key
            self.public_key = public_key
            self.endpoint_ip = endpoint_ip
            self.endpoint_port = endpoint_port
            self.dns_server = dns_server
            # TODO: split junk into sections (H1, H2 etc...)
            self.junk = junk
            self.args, self.kwargs = args, kwargs

    class XrayServer:
        def __init__(
                self,
                host: str,
                port: str,
                web_path: str,
                username: str,
                password: str,
                inbound_id: int,
                token: Optional[str] = None,
                tls: bool = True,
            ):
            self.host = host
            self.port = port
            self.web_path = web_path
            self.username = username
            self.password = password
            self.inbound_id = inbound_id
            self.token = token
            self.tls = tls

    class Core:
        def __init__(self,
                     peer_active_time: int,
                     connection_listen_timer: int,
                     connection_update_timer: int,
                     connection_connected_only_listen_timer: int,
                     logs_path: str):
            self.peer_active_time = peer_active_time
            self.connection_listen_timer = connection_listen_timer
            self.connection_update_timer = connection_update_timer
            self.connection_connected_only_listen_timer = connection_connected_only_listen_timer
            self.logs_path = logs_path

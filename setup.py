import os
from configparser import ConfigParser
from getpass import getpass
from typing import Any, Union

import requests
from colorama import Fore, Style, init

from core.utils.ip_utils import check_ip_address
from core.wg.keygen import generate_private_key, generate_public_key

init(autoreset=True)

def make_config(path):
    # Create pair of crypto keys
    server_private_key = generate_private_key()
    server_public_key = generate_public_key(server_private_key)

    # [TelegramBot]
    print(Style.BRIGHT + "--------- Bot Configuration ---------")
    tg_token = getpass(Fore.YELLOW + "[ ! ]" + Style.RESET_ALL + " Telegram bot token (hidden): ")
    admins = input(Fore.YELLOW + "[ ! ]" + Style.RESET_ALL + " Admin Telegram IDs with ',' separator: ")
    faq_url = input_with_default(Fore.YELLOW + "[ ! ]" + Style.RESET_ALL + " FAQ URL (default: None): ", None)

    # [db]
    print(Style.BRIGHT + "--------- Database Configuration ---------")
    db_path = input_with_default(Fore.YELLOW + "[ ! ]" + Style.RESET_ALL + " Database path (default: db.sqlite): ", "db.sqlite")

    # [core]
    print(Style.BRIGHT + "--------- Core Configuration ---------")
    peer_active_time = input_with_default(
        Fore.YELLOW + "[ ! ]" + Style.RESET_ALL + " Peer active time in hours (default: 12): ", 12
    )
    connection_listen_timer = input_with_default(
        Fore.YELLOW + "[ ! ]" + Style.RESET_ALL + " Connection listen timer in minutes (default: 3): ", 3
    )
    connection_update_timer = input_with_default(
        Fore.YELLOW + "[ ! ]" + Style.RESET_ALL + " Connection update timer in minutes (default: 5): ", 5
    )
    connection_connected_only_listen_timer = input_with_default(
        Fore.YELLOW + "[ ! ]" + Style.RESET_ALL + " Connection connected only listen timer in minutes (default: 1): ", 1
    )
    logs_path = input_with_default(Fore.YELLOW + "[ ! ]" + Style.RESET_ALL + " Logs path (default: logs): ", "logs")
    os.makedirs(logs_path, exist_ok=True)
    os.makedirs(os.path.join(logs_path, "bot"), exist_ok=True)
    os.makedirs(os.path.join(logs_path, "core"), exist_ok=True)
    print(Fore.GREEN + "[ + ]" + Style.RESET_ALL + " Logs path created")

    # [Server]
    print(Style.BRIGHT + "--------- Server Configuration ---------")
    try:
        ip_api = requests.get('https://api.ipify.org', timeout=5)
        if ip_api.status_code != 200:
            raise ValueError
        external_ip = ip_api.content.decode("utf-8")
        print(Fore.GREEN + "[ + ]" + Style.RESET_ALL + " External IP fetched successfully")
    except (requests.exceptions.Timeout, ValueError):
        print(Fore.RED + "ipify is not accessible!")
        external_ip = input(Fore.YELLOW + "[ ! ]" + Style.RESET_ALL + " Enter external ip manually: ")

    ip_range = get_ip_range()
    endpoint_port = get_endpoint_port()

    #Put all data into config
    config = ConfigParser()
    config.optionxform = str
    config["TelegramBot"] = {
        "token": tg_token,
        "admins": admins,
        "faq_url": faq_url,
    }

    config["db"] = {
        "path": db_path
    }

    config["core"] = {
        "peer_active_time": peer_active_time,
        "connection_listen_timer": connection_listen_timer,
        "connection_update_timer": connection_update_timer,
        "connection_connected_only_listen_timer": connection_connected_only_listen_timer,
    }

    config["Server"] = {
        "IP": ip_range,
        "PrivateKey": server_private_key,
        "PublicKey": server_public_key,
        "EndpointIP": external_ip,
        "EndpointPort": endpoint_port,
    }

    with open(path, 'w') as server_config:
        config.write(server_config)

    print(Fore.GREEN + "[ + ]" + Style.RESET_ALL + f" Config file created at {path}. Enjoy your ride!")

def get_ip_range() -> str:
    ip_range = input(Fore.CYAN + "[ ? ]" + Style.RESET_ALL + " Are you okay with '10.28.98.X' range for your IP addresses? Y/N (default: Y) -> ")
    if ip_range.lower() in ["", "y", "yes"]:
        return "10.28.98"
    ip_range = input(Fore.YELLOW + "[ ! ]" + Style.RESET_ALL + " Your IP range ('0.0.0'): ")
    if check_ip_address(ip_range + ".1"):
        return ip_range
    print(Fore.RED + "[ - ] Invalid IP range")
    return get_ip_range()

def get_endpoint_port() -> str:
    endpoint_port = input(Fore.CYAN + "[ ? ]" + Style.RESET_ALL + " Are you okay with 54817 (recommended one) port for your Wireguard Service IP? Y/N (default: Y) -> ")
    if endpoint_port.lower() in ["", "y", "yes"]:
        return "54817"
    return input(Fore.YELLOW + "[ ! ]" + Style.RESET_ALL + " Your endpoint port (check if it's free): ")

def input_with_default(prompt: str, default: Any) -> Union[str, Any]:
    value = input(prompt)
    return value if value else default


if __name__ == "__main__":
    make_config(os.getcwd() + "/config.conf")

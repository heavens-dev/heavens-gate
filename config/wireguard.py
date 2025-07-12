from config.loader import wireguard_server_config
from core.db.db_works import ClientFactory
from core.wg.wg_work import (enable_server, make_wg_server_base_str,
                             peer_to_str_wg_server)


# Rewrite old config/create a brand new one
def create_wg_server_config(path, config_base):
    with open(path, "w", encoding="utf-8") as wg_file:
        wg_file.write(config_base)

# Add peers into config
def update_wg_server_config(path, peer_data):
    with open(path, "a", encoding="utf-8") as wg_file:
        wg_file.write(peer_data)

# Create wireguard server config
def create_server_config(wg_server):
    create_wg_server_config(
        wg_server,
        make_wg_server_base_str(
            wireguard_server_config.user_ip,
            wireguard_server_config.endpoint_port,
            wireguard_server_config.private_key
        )
    )
    peer_list = ClientFactory.select_peers()
    for peer in peer_list:
        # Here I need to check if this peer should be in active server config
        update_wg_server_config(wg_server, peer_to_str_wg_server(peer))

# Func for use once at the beginning of installation
# TODO: check if server was disabled before enabling it
def create_wg_server():
    create_server_config(wireguard_server_config.path)
    enable_server(wireguard_server_config.path)

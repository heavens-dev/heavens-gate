from core.wg.wg_work import create_wg_server_base, peer_for_wg_server_config
from core.wg.wg_work import disable_server, enable_server
from config.settings import Config
from core.db.db_works import Client, ClientFactory
import os

#Rewrite old config/create a brand new one
def create_wg_server_config(path, base):
    with open(path, "w", encoding="utf-8") as wg_file:
            wg_file.write(base)

#Add peers into config
def update_wg_server_config(path, data):
    with open(path, "a", encoding="utf-8") as wg_file:
            wg_file.write(data)

#Create wireguard server config
def create_server_config(wg_server, path_to_config):
    cfg = Config(path_to_config)
    server_cfg = cfg.get_server_config()
    create_wg_server_config(wg_server, create_wg_server_base(server_cfg.user_ip, server_cfg.endpoint_port, server_cfg.private_key))
    peer_list = (ClientFactory.select_peers())
    for peer in peer_list:
        
        update_wg_server_config(wg_server, peer_for_wg_server_config(peer.peer_name, peer.public_key, peer.preshared_key, peer.shared_ips))

#Func for use once at the beginning of installation
def create_wg_server(path_to_config):
    wg_server = os.getcwd()+"/wghub.conf"
    create_wg_server(wg_server, path_to_config)
    enable_server(wg_server)
    return wg_server

#Func for every change of Wireguard server
def recreate_wg_server(wg_server, path_to_config):
    disable_server(wg_server)
    create_server_config(wg_server, path_to_config)
    enable_server(wg_server)
    return wg_server

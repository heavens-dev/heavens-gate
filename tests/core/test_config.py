import pytest

from config.settings import Config


@pytest.fixture
def config_path(tmp_path):
    path = tmp_path / "config.conf"
    with open(path, "w") as config_file:
        config_file.write("""
[TelegramBot]
token=super_secret_token
admins=123, 456

[db]
path=db.sqlite

[core]
peer_active_time=12 # in hours
connection_listen_timer=2 # in seconds
connection_update_timer=5 # in seconds
connection_connected_only_listen_timer=1 # in seconds
logs_path=./logs

[Server]
Path=./wg0.conf
IP=10.0.0
IPMask=32
PrivateKey=super_secret_private_key
EndpointIP=1.1.1.1
EndpointPort=8888
# Junk values that are only used in Amnezia WG. You should not enter them manually!
# setup.py will do all the dirty work for you
Junk=<junk_values>
""")
    return path


def test_load_config(config_path):
    config = Config(config_path)

    bot_cfg = config.get_bot_config()
    assert bot_cfg.token == "super_secret_token"
    assert bot_cfg.admins == [123, 456]
    assert bot_cfg.faq_url is None

    db_cfg = config.get_database_config()
    assert db_cfg.path == "db.sqlite"

    server_cfg = config.get_server_config()
    assert server_cfg.path == "./wg0.conf"
    assert server_cfg.user_ip == "10.0.0"
    assert server_cfg.user_ip_mask == "32"
    assert server_cfg.private_key == "super_secret_private_key"
    assert server_cfg.endpoint_ip == "1.1.1.1"
    assert server_cfg.endpoint_port == "8888"

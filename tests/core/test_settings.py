from configparser import ConfigParser
from unittest.mock import patch

import pytest

from config.settings import Config


def test_bot_settings(config_path):
    config = Config(config_path)

    bot_cfg = config.get_bot_config()

    assert bot_cfg.token == "1234567890:ABCDEF"
    assert bot_cfg.admins == [272727, 282828]
    assert bot_cfg.faq_url == "https://example.com/faq"

def test_faq_url_empty_string(config_path):
    cfg = ConfigParser()
    cfg.read(config_path)
    cfg.set("TelegramBot", "faq_url", "")
    with open(config_path, "w") as f:
        cfg.write(f)
    del cfg

    config = Config(config_path)
    bot_cfg = config.get_bot_config()

    assert bot_cfg.faq_url is None

def test_faq_url_none_string(config_path):
    cfg = ConfigParser()
    cfg.read(config_path)
    cfg.set("TelegramBot", "faq_url", "None")
    with open(config_path, "w") as f:
        cfg.write(f)
    del cfg

    config = Config(config_path)
    bot_cfg = config.get_bot_config()

    assert bot_cfg.faq_url is None

def test_faq_url_no_http(config_path):
    cfg = ConfigParser()
    cfg.read(config_path)
    cfg.set("TelegramBot", "faq_url", "example.com/faq")
    with open(config_path, "w") as f:
        cfg.write(f)
    del cfg

    config = Config(config_path)

    with patch("warnings.warn") as warn:
        bot_cfg = config.get_bot_config()

        assert bot_cfg.faq_url is None
        warn.assert_called_once()

def test_no_token(config_path):
    cfg = ConfigParser()
    cfg.read(config_path)
    cfg.set("TelegramBot", "token", "None")
    with open(config_path, "w") as f:
        cfg.write(f)
    del cfg

    with pytest.raises(ValueError):
        config = Config(config_path)
        config.get_bot_config()

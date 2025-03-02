from datetime import timedelta

import pytest

from core.utils.date_utils import parse_time
from core.utils.ip_utils import (IPQueue, check_ip_address,
                                 generate_ip_addresses, get_ip_prefix)


def test_parse_time():
    assert parse_time("1d") == timedelta(days=1)
    assert parse_time("2w") == timedelta(weeks=2)
    assert parse_time("1M") == timedelta(days=30)
    assert parse_time("1Y") == timedelta(days=365)
    assert parse_time("1d2w3M") == timedelta(days=104)
    assert parse_time("invalid") is None
    assert parse_time("") is None

def test_check_ip_address():
    assert check_ip_address("192.168.1.1") is True
    assert check_ip_address("256.256.256.256") is False
    assert check_ip_address("invalid") is False
    assert check_ip_address("192.168.1") is False

def test_generate_ip_addresses():
    ips = generate_ip_addresses("192.168.1", "30")
    assert len(ips) == 4
    assert "192.168.1.1" in ips
    assert "192.168.1.2" in ips

def test_get_ip_prefix():
    assert get_ip_prefix("192.168.1.1") == "192.168.1"
    assert get_ip_prefix("10.0.0.1") == "10.0.0"

def test_ip_queue():
    ip_list = ["192.168.1.1", "192.168.1.2"]
    queue = IPQueue(ip_list)

    assert queue.count_available_addresses() == 2
    ip = queue.get_ip()
    assert ip in ip_list
    assert queue.count_available_addresses() == 1

    queue.release_ip(ip)
    assert queue.count_available_addresses() == 2

def test_ip_queue_empty():
    queue = IPQueue([])
    with pytest.raises(Exception, match="No IP addresses available"):
        queue.get_ip()

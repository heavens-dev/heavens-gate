import ipaddress


def check_ip_address(ip_address: str) -> bool:
    """Checks if IP address is valid.

    Returns:
        bool: True if IP address is valid. False otherwise.
    """
    try:
        ipaddress.ip_address(ip_address)
        return True
    except ValueError:
        return False

import subprocess

def disable_server(path):
    return "error" in subprocess.getoutput(f"wg-quick down {path}")

def enable_server(path):
    return "error" in subprocess.getoutput(f"wg-quick up {path}")


def make_wg_server_base(ip, endpoint_port, private_key):
    return f"""[Interface]
Address = {ip}.1/24
ListenPort = {endpoint_port}
PrivateKey = {private_key}

"""

def peer_for_wg_server_config(peer_name, public_key, preshared_key, shared_ips):
        return f"""
#{peer_name}
[Peer]
PublicKey = {public_key}
PresharedKey = {preshared_key}
AllowedIPs = {shared_ips}/32

"""
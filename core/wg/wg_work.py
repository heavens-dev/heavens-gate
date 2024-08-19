import subprocess

def disable_server(path):
    return "error" in subprocess.getoutput(f"wg-quick down {path}")

def enable_server(path):
    return "error" in subprocess.getoutput(f"wg-quick up {path}")




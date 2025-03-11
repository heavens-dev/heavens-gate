import subprocess


def generate_preshared_key(is_amnezia: bool = False) -> str:
    command = "wg" if not is_amnezia else "awg"
    return subprocess.run(f"{command} genpsk", check=True, capture_output=True, text=True).stdout

def generate_private_key(is_amnezia: bool = False) -> str:
    command = "wg" if not is_amnezia else "awg"
    # return subprocess.getoutput(f"{command} genkey")
    return subprocess.run(f"{command} genkey", check=True, capture_output=True, text=True).stdout

def generate_public_key(private_key: str, is_amnezia: bool = False) -> str:
    if not private_key:
        raise ValueError("Private key is empty")

    command = "wg" if not is_amnezia else "awg"
    return subprocess.run(
        [command, "pubkey"],
        input=private_key,
        check=True,
        capture_output=True,
        text=True
    ).stdout

if __name__ == "__main__":
    priv_key = generate_private_key()
    pub_key = generate_public_key(priv_key)
    presh_key = generate_preshared_key()
    print(f"Preshared key: {presh_key}")
    print(f"Private key: {priv_key}")
    print(f"Public key: {pub_key}")

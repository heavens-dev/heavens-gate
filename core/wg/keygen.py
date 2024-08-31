import subprocess


def preshared_key():
    return subprocess.getoutput("wg genpsk")

def private_key():
    return subprocess.getoutput("wg genkey")

def public_key(private_key):
    return subprocess.getoutput(f"echo {private_key} | wg pubkey ")

if __name__ == "__main__":
    priv_key = private_key()
    pub_key = public_key(private_key)
    presh_key = preshared_key()
    print(f"Here your Preshared key {presh_key}")
    print(f"Here your Private key {priv_key}")
    print(f"Here your Public key {pub_key}")

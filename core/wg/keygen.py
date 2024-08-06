import subprocess

def preshared_key():
    return subprocess.getoutput("wg genpsk")

def private_key():
    return subprocess.getoutput("wg genkey")

def public_key(private_key):
    return subprocess.getoutput(f"echo {private_key} | wg pubkey ")

if __name__ == "__main__":
    private_key = private_key()
    public_key = public_key(private_key)
    preshared_key = preshared_key()
    print(f"Here your Preshared key {preshared_key}")
    print(f"Here your Private key {private_key}")
    print(f"Here your Public key {public_key}")



import hashlib

def sha256(data: str):
    return hashlib.sha256(data.encode()).hexdigest()


def shorten_key(key: str):
    """Display a shorter version of public keys for logging."""
    return key[:10] + "..." + key[-10:]
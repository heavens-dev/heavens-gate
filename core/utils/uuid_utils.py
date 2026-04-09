import hashlib
import uuid


def generate_deterministic_uuid_string(input_string: str) -> uuid.UUID:
    """Creates a consistent UUID using a hash of the input string

    Args:
        input_string (str): String to be converted to UUID

    Returns:
        uuid.UUID: Converted string
    """
    hash_object = hashlib.md5(input_string.encode())
    return str(uuid.UUID(hex=hash_object.hexdigest()))

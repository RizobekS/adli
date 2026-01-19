# apps/telephony/crypto.py
import os
from cryptography.fernet import Fernet

def _get_fernet() -> Fernet:
    key = os.getenv("TELEPHONY_FERNET_KEY", "").strip()
    if not key:
        raise RuntimeError("TELEPHONY_FERNET_KEY is not set")
    return Fernet(key.encode())

def encrypt_str(s: str) -> str:
    f = _get_fernet()
    return f.encrypt(s.encode()).decode()

def decrypt_str(token: str) -> str:
    f = _get_fernet()
    return f.decrypt(token.encode()).decode()

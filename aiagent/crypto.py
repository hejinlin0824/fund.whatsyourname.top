import os
from cryptography.fernet import Fernet
from django.conf import settings


def get_fernet() -> Fernet:
    key = os.environ.get("JK_FERNET_KEY") or getattr(settings, "JK_FERNET_KEY", None)
    if not key:
        key = Fernet.generate_key().decode()
        env_path = settings.BASE_DIR / ".env"
        with open(env_path, "a") as f:
            f.write(f"\nJK_FERNET_KEY={key}\n")
        os.environ["JK_FERNET_KEY"] = key
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_key(plain: str) -> str:
    if not plain:
        return ""
    return get_fernet().encrypt(plain.encode()).decode()


def decrypt_key(enc: str) -> str:
    if not enc:
        return ""
    return get_fernet().decrypt(enc.encode()).decode()

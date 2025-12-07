import base64
import os
from typing import Iterable, List, Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

_USB_BASES = ['/media', '/run/media', '/mnt']
_ENC_HEADER = b"TCENC1"  # Simple header to identify encrypted exports
_RUNTIME_EXPORT_PASSPHRASE: Optional[str] = None
_PASSPHRASE_ENV = "TIMECLOCK_ENCRYPTION_KEY"


def _iter_mounts(base: str) -> Iterable[str]:
    if not os.path.isdir(base):
        return
    for name in os.listdir(base):
        path = os.path.join(base, name)
        if os.path.ismount(path):
            yield path
        elif os.path.isdir(path):
            for child in os.listdir(path):
                child_path = os.path.join(path, child)
                if os.path.ismount(child_path):
                    yield child_path


def find_usb_mounts() -> List[str]:
    """
    Return a list of available USB mountpoints.
    """
    mounts = []
    for base in _USB_BASES:
        mounts.extend(_iter_mounts(base))
    return mounts


def get_export_directory(prefer_usb: bool = True) -> str:
    """
    Determine where exports should be written.

    Priority:
    1. `TIME_CLOCK_EXPORT_PATH` environment variable (expanded)
    2. First mounted USB drive under /media, /run/media, /mnt
    3. Local `exports/` directory inside the application folder
    """
    env_path = os.getenv('TIME_CLOCK_EXPORT_PATH')
    if env_path:
        target = os.path.expanduser(env_path)
    else:
        usb_mounts = find_usb_mounts() if prefer_usb else []
        if usb_mounts:
            target = usb_mounts[0]
        else:
            target = os.path.join(os.getcwd(), 'exports')

    os.makedirs(target, exist_ok=True)
    return target


class ExportEncryptionError(Exception):
    """Raised when export encryption passphrase is unavailable."""


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    """Derive a Fernet key from a human passphrase."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=200_000,
    )
    return base64.urlsafe_b64encode(kdf.derive(passphrase.encode('utf-8')))


def get_export_passphrase() -> str:
    """
    Read the export encryption passphrase from environment.
    Raises ExportEncryptionError if missing.
    """
    if _RUNTIME_EXPORT_PASSPHRASE:
        return _RUNTIME_EXPORT_PASSPHRASE

    passphrase = os.getenv(_PASSPHRASE_ENV)
    if not passphrase:
        raise ExportEncryptionError(
            f"Export passphrase missing. Set {_PASSPHRASE_ENV} or enter it in the app before exporting."
        )
    return passphrase


def set_runtime_export_passphrase(passphrase: str) -> None:
    """
    Set the export passphrase for the current session (in-memory only).
    """
    global _RUNTIME_EXPORT_PASSPHRASE
    _RUNTIME_EXPORT_PASSPHRASE = passphrase


def has_export_passphrase() -> bool:
    """Return True if a passphrase is available (runtime or environment)."""
    return bool(_RUNTIME_EXPORT_PASSPHRASE or os.getenv(_PASSPHRASE_ENV))


def encrypt_bytes(data: bytes, passphrase: str) -> bytes:
    """Encrypt arbitrary bytes using Fernet with a PBKDF2-derived key."""
    salt = os.urandom(16)
    key = _derive_key(passphrase, salt)
    token = Fernet(key).encrypt(data)
    return _ENC_HEADER + salt + token


def write_encrypted_file(data: bytes, target_path: str, passphrase: Optional[str] = None) -> str:
    """
    Encrypt data and write to target_path.

    Args:
        data: Raw bytes to encrypt.
        target_path: Destination path (will be created).
        passphrase: Optional override; otherwise read from env.

    Returns:
        The path written to.
    """
    passphrase = passphrase or get_export_passphrase()
    payload = encrypt_bytes(data, passphrase)
    os.makedirs(os.path.dirname(target_path) or ".", exist_ok=True)
    with open(target_path, "wb") as f:
        f.write(payload)
    return target_path


def ensure_export_passphrase() -> bool:
    """
    Check that a passphrase is configured via environment.
    Returns True if present (env or runtime), False if missing.
    """
    return has_export_passphrase()


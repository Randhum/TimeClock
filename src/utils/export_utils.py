"""
Export utilities for the TimeClock application.
Handles USB mount detection and export directory management.
"""
import os
from typing import Iterable, List

_USB_BASES = ['/media', '/run/media', '/mnt']


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


def write_file(data: bytes, target_path: str) -> str:
    """
    Write data to target_path.

    Args:
        data: Raw bytes to write.
        target_path: Destination path (will be created).

    Returns:
        The path written to.
    """
    os.makedirs(os.path.dirname(target_path) or ".", exist_ok=True)
    with open(target_path, "wb") as f:
        f.write(data)
    return target_path

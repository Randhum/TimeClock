"""
Hardware layer for TimeClock application.

Contains RFID reader drivers and hardware configuration utilities.
"""

from .pcprox import open_pcprox
from .rfid import get_rfid_provider, RFIDProvider, PcProxRFIDProvider, MockRFIDProvider

__all__ = [
    'open_pcprox',
    'get_rfid_provider',
    'RFIDProvider',
    'PcProxRFIDProvider',
    'MockRFIDProvider',
]


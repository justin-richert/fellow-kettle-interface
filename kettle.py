"""Manage fellow-py connection."""

import asyncio
import enum
import logging
import os

import fellow_py

_KETTLE_FILL_LEVEL_MAPPING = {}
_KETTLE_LOCK = asyncio.Lock()
_KETTLE_MAC_ADDRESS = "00:1C:97:19:49:4D"
_KETTLE: fellow_py.StaggEKGPlusKettle = None

LOG_LEVEL = os.getenv("LOG_LEVEL", "warning").upper()
LOGGER = logging.getLogger("kettle")
LOGGER.setLevel(LOG_LEVEL)


class KettleFillLevel(enum.Enum):
    """Enum to define kettle fill states."""

    LOW = 1
    MEDIUM = 2
    FULL = 3


def connect(func):
    """Ensure kettle connection and yield kettle instance."""

    async def _connect(*args, **kwargs):
        """Connect to the physical kettle."""
        global _KETTLE

        async with _KETTLE_LOCK:
            if not _KETTLE or not _KETTLE.is_connected:
                LOGGER.info("Kettle not connected... attempting to connect")
                _KETTLE = await fellow_py.discover_by_address(_KETTLE_MAC_ADDRESS)
                await _KETTLE.connect()
        await func(_KETTLE, *args, **kwargs)

    return _connect


def guess_fill_level():
    """Use the FSR reader average tick diff to guess kettle fill level."""

    # TODO: Define the mapping and actually use it
    return KettleFillLevel.FULL

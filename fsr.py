"""FSR Sensor reader."""

import asyncio
import logging
import os

import asyncpio

# define the pin that goes to the circuit
PIN_TO_CIRCUIT = 4

LOG_LEVEL = os.getenv("LOG_LEVEL", "warning").upper()
LOGGER = logging.getLogger("fsr")
LOGGER.setLevel(LOG_LEVEL)


_FSR_READER_INSTANCE = None


class FSRReader:
    """Class responsible for managing interfacing with asyncpio to read FSR sensor."""

    def __init__(self, pi, gpio):
        """Initialize the FSR Reader."""

        self.pi = pi
        self.gpio = gpio

        self.t1 = None
        self.t2 = None
        self.t3 = None
        self.t4 = None

    @classmethod
    async def create(cls, pi, gpio):
        """Async initialization method."""

        self = cls(pi, gpio)

        await self._trigger_circuit()

        self.cb = await pi.callback(gpio, asyncpio.RISING_EDGE, self._cb)
        LOGGER.info("Callback for rising edge on pin %s created", gpio)
        return self

    @property
    def average_tick_diff(self):
        """Using the average tick diff from last 4 callbacks, guess the kettle fill level."""

        if not (self.t1 and self.t2 and self.t3 and self.t4):
            raise Exception("Have not yet received enough data from FSR circuit!")

        average_tick_diff = (
            asyncpio.tickDiff(self.t1, self.t2)
            + asyncpio.tickDiff(self.t2, self.t3)
            + asyncpio.tickDiff(self.t3, self.t4)
        ) / 3
        LOGGER.debug("Average tickDiff: %s", average_tick_diff)

        return average_tick_diff

    async def _trigger_circuit(self):
        """Run a sequence of steps to trigger the circuit."""

        await self.pi.set_mode(PIN_TO_CIRCUIT, asyncpio.OUTPUT)
        await self.pi.write(PIN_TO_CIRCUIT, 0)
        await asyncio.sleep(0.1)
        await self.pi.set_mode(PIN_TO_CIRCUIT, asyncpio.INPUT)

    async def _cb(self, _, __, tick):
        """Handle rising edge callback."""

        LOGGER.info("Callback received: %s - %s - %s", _, __, tick)

        for i in range(1, 5):
            if not getattr(self, f"t{i}"):
                setattr(self, f"t{i}", tick)
                break

        self.t1 = self.t2
        self.t2 = self.t3
        self.t3 = self.t4
        self.t4 = tick

        await self._trigger_circuit()

    async def cancel(self):
        """Cancel the callback."""

        await self.cb.cancel()
        LOGGER.debug("Asyncpio callback successfully cancelled")


async def get_average_tick_diff():
    """Return average tick diff for fsr circuit."""

    if not _FSR_READER_INSTANCE:
        raise Exception("Please initialize by calling the run method first!")

    return _FSR_READER_INSTANCE.average_tick_diff


async def run():
    """Read data from the FSR circuit."""
    global _FSR_READER_INSTANCER

    pi = asyncpio.pi()
    await pi.connect()
    LOGGER.info("Successfully connected to pigpiod!")

    _FSR_READER_INSTANCE = await FSRReader.create(pi, PIN_TO_CIRCUIT)
    LOGGER.info("Created FSRReader instance")

    while True:
        try:
            await asyncio.sleep(15)
        except (KeyboardInterrupt, asyncio.CancelledError):
            LOGGER.info("Shutting down...")
            await _FSR_READER_INSTANCE.cancel()
            await pi.stop()


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(run())

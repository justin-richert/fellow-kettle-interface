"""Master script.

- Connects to MQTT and Kettle and manages communication between the two.
- Starts FSR reader.
"""

import asyncio
import logging
import os
import typing

import fellow_py

import fsr
import kettle
import mqtt

LOG_LEVEL = os.getenv("LOG_LEVEL", "warning").upper()
LOGGER = logging.getLogger()
LOGGER.setLevel(LOG_LEVEL)


@kettle.connect
async def publish_kettle_info(k: fellow_py.StaggEKGPlusKettle):
    """Periodically publish kettle info."""

    try:
        await asyncio.gather(
            mqtt.publish(mqtt.KETTLE_POWER_STATE, "on" if k.is_on else "off"),
            mqtt.publish(mqtt.KETTLE_CURRENT_TEMP, k.current_temperature),
            mqtt.publish(mqtt.KETTLE_TARGET_TEMP, k.target_temperature),
            mqtt.publish(mqtt.KETTLE_WARMING_RATE, k.average_warming_rate),
            mqtt.publish(mqtt.KETTLE_FILL_LEVEL, kettle.guess_fill_level().name),
        )
    except BaseException as e:
        LOGGER.exception(e)

    await asyncio.sleep(5)


@kettle.connect
async def kettle_action_callback(
    k: fellow_py.StaggEKGPlusKettle,
    topic: mqtt.aiomqtt.Topic,
    payload: typing.Union[int, float, str, bytes, type(None)],
):
    """Callback for handling messages on the action topic.

    Payloads are allowed to be any of the listed types in the hint, but we
    always expect string presently, so simplifying logic accordingly.
    """

    topic = topic.value

    try:
        payload = payload.decode("utf8")
    except BaseException:
        raise Exception(f"Unable to handle payload {payload} on topic {topic}")

    match topic:
        case mqtt.KETTLE_POWER_TOGGLE:
            match payload:
                case "on":
                    await k.turn_on()
                case "off":
                    await k.turn_off()
                case _:
                    raise Exception(f"Unrecognized payload {payload} for power toggle")
        case mqtt.KETTLE_SET_TARGET_TEMP:
            try:
                new_temp = int(payload)
            except ValueError:
                raise Exception(f"Unrecognized payload {payload} for setting target temp")

            await k.set_target_temperature(new_temp)
        case _:
            LOGGER.warning("Unhandled topic %s", topic)


async def main():
    """Execute all the things and run forever-ish."""

    await asyncio.gather(
        publish_kettle_info(),
        mqtt.subscribe(mqtt.KETTLE_ACTION_WILDCARD, kettle_action_callback),
        fsr.run(),
    )


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(main())

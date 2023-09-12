"""MQTT processing."""

import asyncio
import logging
import os
import typing

import aiomqtt

LOG_LEVEL = os.getenv("LOG_LEVEL", "warning").upper()
LOGGER = logging.getLogger("mqtt")
LOGGER.setLevel(LOG_LEVEL)

MQTT_HOST = os.getenv("MQTT_HOST")
MQTT_USERNAME = os.getenv("MQTT_USERNAME")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")


# TOPIC DEFINITIONS
# STATE INFO
KETTLE_POWER_STATE = "fellow/kettle/status/power"
KETTLE_CURRENT_TEMP = "fellow/kettle/status/current_temperature"
KETTLE_TARGET_TEMP = "fellow/kettle/status/target_temperature"
KETTLE_WARMING_RATE = "fellow/kettle/status/warming_rate"
KETTLE_FILL_LEVEL = "fellow/kettle/status/fill_level"

# ACTIONS
KETTLE_ACTION_WILDCARD = "fellow/kettle/action/#"
KETTLE_POWER_TOGGLE = "fellow/kettle/action/power"
KETTLE_SET_TARGET_TEMP = "fellow/kettle/action/target_temperature"


async def subscribe(topic: str, callback: typing.Awaitable):
    """Subscribe to a given topic and send each incoming message to the supplied callback."""

    async with aiomqtt.Client(MQTT_HOST, username=MQTT_USERNAME, password=MQTT_PASSWORD) as client:
        async with client.messages() as messages:
            await client.subscribe(topic)
            try:
                async for message in messages:
                    await callback(message.topic, message.payload)
            except BaseException as e:
                LOGGER.exception(e)
                if isinstance(e, (asyncio.CancelledError, KeyboardInterrupt)):
                    await client.unsubscribe(topic)


async def publish(topic: str, payload: typing.Union[int, float, str, bytes, type(None)]):
    """Publish a given payload onto a given topic."""

    async with aiomqtt.Client(MQTT_HOST, username=MQTT_USERNAME, password=MQTT_PASSWORD) as client:
        await client.publish(topic, payload=payload)

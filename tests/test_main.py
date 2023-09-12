"""Test functions in main.py."""

import unittest.mock

import fellow_py
import pytest

import mqtt

MOCK_KETTLE = unittest.mock.Mock(spec=fellow_py.StaggEKGPlusKettle)


@pytest.fixture(autouse=True)
async def _():
    """Reset mock kettle."""
    yield
    MOCK_KETTLE.reset_mock()


def _mock_connect(func):
    """Mock connect decorator to return a fake stagg kettle object."""

    async def _connect(*args, **kwargs):
        """Build a mock autospecced to StaggEKGPlusKettle and return."""

        MOCK_KETTLE.is_on = True
        MOCK_KETTLE.current_temperature = 123
        MOCK_KETTLE.target_temperature = 212
        MOCK_KETTLE.average_warming_rate = 1.0
        await func(MOCK_KETTLE, *args, **kwargs)

    return _connect


class TestPublishKettleInfo:
    """Test the publish_kettle_info function."""

    @unittest.mock.patch("main.mqtt.publish")
    @unittest.mock.patch("main.asyncio.sleep")
    @unittest.mock.patch("kettle.connect", _mock_connect)
    async def test(self, _, mock_publish):
        """Test that the expected publish calls are made."""

        import main

        await main.publish_kettle_info()
        assert mock_publish.call_count == 5
        mock_publish.assert_any_call(mqtt.KETTLE_POWER_STATE, "on")
        mock_publish.assert_any_call(mqtt.KETTLE_CURRENT_TEMP, 123)
        mock_publish.assert_any_call(mqtt.KETTLE_TARGET_TEMP, 212)
        mock_publish.assert_any_call(mqtt.KETTLE_WARMING_RATE, 1.0)
        mock_publish.assert_any_call(mqtt.KETTLE_FILL_LEVEL, "FULL")


class TestKettleActionCallback:
    """Test that incoming mqtt messages on the action topic are properly handled."""

    @unittest.mock.patch("kettle.connect", _mock_connect)
    @pytest.mark.parametrize(
        "topic,payload",
        [
            (mqtt.KETTLE_POWER_TOGGLE, b"on"),
            (mqtt.KETTLE_POWER_TOGGLE, b"off"),
            (mqtt.KETTLE_SET_TARGET_TEMP, b"123"),
        ],
    )
    async def test(self, _, topic, payload):
        """Test happy path kettle action callback cases."""

        import main

        await main.kettle_action_callback(mqtt.aiomqtt.Topic(topic), payload)

        if topic == mqtt.KETTLE_POWER_TOGGLE and payload == b"on":
            MOCK_KETTLE.turn_on.assert_called_once_with()
        elif topic == mqtt.KETTLE_POWER_TOGGLE and payload == b"off":
            MOCK_KETTLE.turn_off.assert_called_once_with()
        else:
            MOCK_KETTLE.set_target_temperature.assert_called_once_with(123)

    @unittest.mock.patch("main.LOGGER")
    @unittest.mock.patch("kettle.connect", _mock_connect)
    async def test_unknown_topic(self, mock_logger):
        """Test bad topic received in callback."""

        import main

        await main.kettle_action_callback(mqtt.aiomqtt.Topic("unknown/topic"), b"doesn't matter")
        mock_logger.warning.assert_called_once_with("Unhandled topic %s", "unknown/topic")

    @unittest.mock.patch("kettle.connect", _mock_connect)
    async def test_bad_payload_type(self):
        """Test that a bad payload throws a specific exception."""

        import main

        with pytest.raises(
            Exception, match=f"Unable to handle payload None on topic {mqtt.KETTLE_POWER_TOGGLE}"
        ):
            await main.kettle_action_callback(mqtt.aiomqtt.Topic(mqtt.KETTLE_POWER_TOGGLE), None)

    @unittest.mock.patch("kettle.connect", _mock_connect)
    @pytest.mark.parametrize(
        "topic,payload",
        [
            (mqtt.KETTLE_POWER_TOGGLE, b"onandoff"),
            (mqtt.KETTLE_SET_TARGET_TEMP, b"abc"),
        ],
    )
    async def test_bad_payload_contents(self, topic, payload):
        """Test sending bad payload values to the two expected topics."""

        import main

        expected_error_message = (
            "Unrecognized payload onandoff for power toggle"
            if topic == mqtt.KETTLE_POWER_TOGGLE
            else "Unrecognized payload abc for setting target temp"
        )

        with pytest.raises(Exception, match=expected_error_message):
            await main.kettle_action_callback(mqtt.aiomqtt.Topic(topic), payload)

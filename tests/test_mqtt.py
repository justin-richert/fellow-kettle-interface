"""Test mqtt client logic."""

import asyncio

import mqtt


class TestSubscribeAndPublish:
    """Test the subscribe mqtt client functionality."""

    async def test(self):
        """Test subscribing to a topic."""

        callback_values = []

        async def callback(topic, payload):
            """Up the callback counter."""
            callback_values.append((topic.value, payload))

        task = asyncio.create_task(mqtt.subscribe("my/topic/#", callback))

        await asyncio.sleep(0.5)
        await mqtt.publish("my/topic/a", "a")
        await mqtt.publish("my/topic/b", "b")
        await mqtt.publish("my/topic/a/b", "c")
        await asyncio.sleep(0.5)

        assert sorted(callback_values, key=lambda _: _[1]) == [
            ("my/topic/a", b"a"),
            ("my/topic/b", b"b"),
            ("my/topic/a/b", b"c"),
        ]

        task.cancel()
        await task

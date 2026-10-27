#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A `msg_type=3` push must keep its envelope, like a polled record keeps its raw item.

`_fire_notification()` flattens `msg_content` into the top-level notification
dict (service_type/msg_id/code/message plus the extra content fields), which
drops the envelope the broker actually sent. That envelope is where a field the
integration does not know about lives, so it is snapshotted as `raw` (copied
from the pre-flattening `data`) exactly as `parse_notification_item()` snapshots
a Message Centre item. `record_notification()` keeps an existing `raw` rather
than replacing it.

Home Assistant is not importable here; `mqtt_client.py` imports only paho at
module scope, so paho is stubbed when it is not installed - the same pattern the
rest of the suite uses for `cryptography`.

    python3 tests/test_mqtt_notification_raw.py
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys
import types
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _component  # noqa: E402


def _stub_paho() -> None:
    """Stand in for paho's client module, which the host may not have."""
    try:
        import paho.mqtt.client  # noqa: F401
        return
    except ImportError:
        pass

    class _Client:
        def __init__(self, *args, **kwargs) -> None:
            pass

    paho = types.ModuleType("paho")
    paho_mqtt = types.ModuleType("paho.mqtt")
    paho_mqtt_client = types.ModuleType("paho.mqtt.client")
    paho_mqtt_client.Client = _Client
    paho_mqtt_client.MQTTv311 = 4
    paho_mqtt_client.CallbackAPIVersion = types.SimpleNamespace(VERSION2=2)
    paho_mqtt_client.MQTTMessage = object
    paho_mqtt.client = paho_mqtt_client
    paho.mqtt = paho_mqtt
    sys.modules["paho"] = paho
    sys.modules["paho.mqtt"] = paho_mqtt
    sys.modules["paho.mqtt.client"] = paho_mqtt_client


_stub_paho()

_spec = importlib.util.spec_from_file_location(
    "mqtt_client_raw_t", _component.module_path("mqtt_client.py"))
assert _spec and _spec.loader
mqtt_client = importlib.util.module_from_spec(_spec)
sys.modules["mqtt_client_raw_t"] = mqtt_client
_spec.loader.exec_module(mqtt_client)


def _client():
    client = mqtt_client.XPengMQTTClient(
        client_id="xmart:app:1:abc", password="pw",
        server="broker.example:8885", user_id="1",
    )
    received: list[dict] = []
    client.set_notification_callback(received.append)
    return client, received


class TestPushRawRecord(unittest.TestCase):
    PUSH = {
        "msg_type": 3,
        "service_type": 12,
        "msg_id": "abc123",
        "msg_content": {"code": 0, "msg": "Window open", "window": 1},
    }

    def test_envelope_is_preserved_as_raw(self):
        client, received = _client()
        client._fire_notification(self.PUSH)
        self.assertEqual(len(received), 1)
        raw = received[0]["raw"]
        # The flattened fields still work...
        self.assertEqual(received[0]["message"], "Window open")
        self.assertEqual(received[0]["window"], 1)
        # ...and the envelope that flattening drops is still there.
        self.assertEqual(raw["msg_type"], 3)
        self.assertEqual(raw["msg_content"], self.PUSH["msg_content"])
        self.assertEqual(raw, self.PUSH)

    def test_raw_is_a_copy_and_the_payload_is_not_mutated(self):
        client, received = _client()
        push = {
            "msg_type": 3,
            "service_type": 12,
            "msg_id": "m",
            "msg_content": {"code": 0, "msg": "x"},
        }
        client._fire_notification(push)
        self.assertIsNot(received[0]["raw"], push)
        # record_notification adds timestamp/local_time later; nothing of that
        # may already be in the push dict, or raw would carry derived fields.
        self.assertNotIn("timestamp", push)
        self.assertNotIn("local_time", push)
        self.assertNotIn("raw", push)

    def test_falsy_raw_is_still_present(self):
        client, received = _client()
        client._fire_notification({"msg_type": 3, "msg_content": {}})
        self.assertEqual(received[0]["raw"], {"msg_type": 3, "msg_content": {}})

    def test_msg_content_key_named_raw_cannot_displace_the_envelope(self):
        """`raw` is reserved: the wire envelope wins over a content field."""
        client, received = _client()
        client._fire_notification({
            "msg_type": 3, "msg_id": "m",
            "msg_content": {"code": 0, "msg": "x", "raw": "from content"},
        })
        raw = received[0]["raw"]
        self.assertIsInstance(raw, dict)
        self.assertEqual(raw["msg_id"], "m")
        self.assertEqual(raw["msg_content"]["raw"], "from content")


if __name__ == "__main__":
    unittest.main(verbosity=2)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A recorded notification must keep XPENG's claimed time and stamp the real latency.

`record_notification()` used to overwrite `timestamp` — parsed from the Message
Centre `createTime` — with the collection time. The sensor then computed
`delay_s = now - timestamp`, which grew on every read (it measured "age since
this poll") instead of the poll latency, and automations lost the claimed time
even though the docs promised it. `timestamp_raw`/`raw` were the only way back.

The contract these tests pin:

1. a polled item keeps its claimed `timestamp`;
2. `collected_at` is the instant `record_notification()` ran;
3. `delay_s` = collected_at - claimed, stamped once (None when unparseable);
4. a `msg_type=3` push has no claimed time, so it gets the arrival time and a
   zero delay;
5. an existing `raw` is never replaced.

The coordinator imports Home Assistant, which this host does not have, so the
function is extracted from the source with `ast` and run against a fake self -
the same pattern `test_rest_notifications.py` uses for `_notification_id`.

    python3 tests/test_notification_delay.py
"""

from __future__ import annotations

import ast
import collections
import importlib.util
import logging
import pathlib
import sys
import types
import typing
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _component  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "poll_status", _component.module_path("poll_status.py"))
assert _spec and _spec.loader
poll = importlib.util.module_from_spec(_spec)
sys.modules["poll_status"] = poll
_spec.loader.exec_module(poll)

FIXED_NOW = datetime(2026, 10, 27, 10, 34, 15, 320832, tzinfo=timezone.utc)
# What parse_notification_item() produces from createTime: no timezone, so it is
# read as this machine's local time. Derived from FIXED_NOW so the 29 s latency
# is the same assertion on any host timezone.
CLAIMED = (
    FIXED_NOW.astimezone().replace(tzinfo=None) - timedelta(seconds=29)
).isoformat()


class _FakeDatetime:
    """Freeze `datetime.now(timezone.utc)` for the function under test."""

    @staticmethod
    def now(tz=None):
        return FIXED_NOW


def _load_record_notification():
    tree = ast.parse(
        (_component.component_dir() / "coordinator.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "record_notification":
            module = ast.Module(body=[node], type_ignores=[])
            namespace: dict[str, typing.Any] = {
                "datetime": _FakeDatetime,
                "timezone": timezone,
                "poll_status": poll,
                "Any": typing.Any,
                "_LOGGER": logging.getLogger("test_notification_delay"),
            }
            exec(compile(module, "<record_notification>", "exec"), namespace)
            return namespace["record_notification"]
    raise AssertionError("record_notification not found in coordinator.py")


record_notification = _load_record_notification()


class _FakeCoordinator:
    def __init__(self) -> None:
        self.notifications = collections.deque(maxlen=50)
        self.notification_count = 0
        self.listener_log: list[str] = []
        self._last_full_data: dict = {}
        self.fired: list[tuple[str, dict]] = []
        self.updated = None
        self.hass = types.SimpleNamespace(
            bus=types.SimpleNamespace(async_fire=self._fire))

    def _fire(self, event_type: str, data: dict) -> None:
        self.fired.append((event_type, data))

    def _now_str(self) -> str:
        return "21:34:15"

    def async_set_updated_data(self, data) -> None:
        self.updated = data


def _record(notification: dict) -> tuple[_FakeCoordinator, dict]:
    coordinator = _FakeCoordinator()
    record_notification(coordinator, notification)
    return coordinator, notification


class TestPolledItemKeepsItsClaim(unittest.TestCase):
    def test_claimed_timestamp_survives(self):
        _, note = _record({"id": "1", "timestamp": CLAIMED, "source": "rest"})
        self.assertEqual(note["timestamp"], CLAIMED)

    def test_collected_at_is_the_recording_instant(self):
        _, note = _record({"id": "1", "timestamp": CLAIMED})
        self.assertEqual(note["collected_at"], FIXED_NOW.isoformat())

    def test_delay_is_collected_minus_claimed_and_stamped(self):
        _, note = _record({"id": "1", "timestamp": CLAIMED})
        self.assertAlmostEqual(note["delay_s"], 29.0, delta=0.001)
        # ...and it is the same number the helper would give for the two
        # timestamps now stored on the record.
        self.assertAlmostEqual(
            note["delay_s"],
            poll.notification_delay_seconds(CLAIMED, FIXED_NOW.timestamp()),
            delta=1e-6,
        )
        # The two fields the sensor needs are already on the record, so a read
        # cannot change the answer (no now-timestamp in the expression).
        self.assertIn("delay_s", note)
        self.assertIn("collected_at", note)

    def test_raw_is_the_record_before_the_derived_fields(self):
        _, note = _record({
            "id": "1", "timestamp": CLAIMED,
            "messageContent": '{"msgContent":{"description":"<p>x</p>"}}',
        })
        raw = note["raw"]
        self.assertEqual(raw["timestamp"], CLAIMED)
        self.assertEqual(raw["messageContent"],
                         '{"msgContent":{"description":"<p>x</p>"}}')
        for derived in ("raw", "collected_at", "delay_s", "local_time"):
            self.assertNotIn(derived, raw)


class TestPushHasNoClaim(unittest.TestCase):
    def test_arrival_time_and_zero_delay(self):
        _, note = _record({"service_type": 12, "msg_id": "m", "message": "x"})
        self.assertEqual(note["timestamp"], FIXED_NOW.isoformat())
        self.assertEqual(note["delay_s"], 0.0)
        self.assertEqual(note["collected_at"], FIXED_NOW.isoformat())

    def test_existing_raw_wins_over_the_snapshot(self):
        wire = {"msg_type": 3, "msg_content": {"msg": "x"}}
        _, note = _record({"service_type": 12, "raw": wire})
        self.assertIs(note["raw"], wire)


class TestUnusableClaim(unittest.TestCase):
    def test_unparseable_timestamp_is_kept_but_delay_is_none(self):
        _, note = _record({"timestamp": "not a time"})
        self.assertEqual(note["timestamp"], "not a time")
        self.assertIsNone(note["delay_s"])


class TestRecordingSideEffects(unittest.TestCase):
    def test_event_fires_with_the_recorded_dict(self):
        coordinator, note = _record({"id": "7", "timestamp": CLAIMED})
        self.assertEqual(len(coordinator.fired), 1)
        event_type, payload = coordinator.fired[0]
        self.assertEqual(event_type, "xpeng_notification")
        self.assertIs(payload, note)
        self.assertIn("delay_s", payload)

    def test_counted_and_buffered(self):
        coordinator, note = _record({"service_type": 9, "code": 0, "message": "hi"})
        self.assertEqual(coordinator.notification_count, 1)
        self.assertEqual(list(coordinator.notifications), [note])
        self.assertTrue(coordinator.listener_log)
        self.assertIsNotNone(coordinator.updated)


if __name__ == "__main__":
    unittest.main(verbosity=2)

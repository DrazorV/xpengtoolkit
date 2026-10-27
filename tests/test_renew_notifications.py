#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A successful renewal only raises a notification when the install wants one.

A renewal runs on its own timer, so the success card is the one that repeats every
100 minutes. The option silences exactly that card: failures keep notifying after two
consecutive attempts, because those are the ones an owner has to see.

The module is imported by path; it reads its options from the Supervisor at import
time and tolerates their absence, so a bare interpreter is enough.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _component  # noqa: E402

SERVER_PATH = ROOT / "xpeng_renew" / "renew_server.py"


def _load():
    spec = importlib.util.spec_from_file_location(
        "renew_server_notify_test", SERVER_PATH
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["renew_server_notify_test"] = module
    try:
        spec.loader.exec_module(module)
    except ImportError as exc:  # pragma: no cover - stdlib only today
        raise unittest.SkipTest(f"renew_server.py could not be imported: {exc}")
    return module


server = _load()


class TestSuccessNotification(unittest.TestCase):
    def setUp(self):
        server.STATE["renewals"] = 0
        server.STATE["failures"] = 0
        server.STATE["consecutive_failures"] = 0

    def _record(self, enabled: bool, result: dict) -> mock.Mock:
        with (
            mock.patch.object(server, "NOTIFY_ON_SUCCESS", enabled),
            mock.patch.object(server, "_log"),
            mock.patch.object(server, "_notify") as notify,
        ):
            server._record_result(result)
        return notify

    def test_a_success_notifies_by_default(self):
        notify = self._record(True, {"ok": True, "ms": 12})
        notify.assert_called_once_with(
            "XPENG credentials renewed", "A fresh token pair was imported."
        )

    def test_a_success_can_be_silent(self):
        notify = self._record(False, {"ok": True, "ms": 12})
        notify.assert_not_called()

    def test_failures_still_notify_when_success_is_silent(self):
        notify = self._record(False, {"ok": False, "error": "boom"})
        notify.assert_not_called()
        notify = self._record(False, {"ok": False, "error": "boom"})
        notify.assert_called_once()
        self.assertEqual(notify.call_args.args[0], "XPENG renewal failing")

    def test_a_success_resets_the_failure_streak(self):
        server.STATE["consecutive_failures"] = 1
        self._record(False, {"ok": True, "ms": 1})
        self.assertEqual(server.STATE["consecutive_failures"], 0)


class TestSettingBool(unittest.TestCase):
    def test_supervisor_boolean_option(self):
        with mock.patch.dict(server.OPTIONS, {"notify_on_success": False}, clear=False):
            self.assertFalse(server._setting_bool("notify_on_success", True))
            self.assertTrue(server._setting_bool("not_a_real_option", True))

    def test_environment_string(self):
        with mock.patch.dict(server.os.environ, {"NOTIFY_ON_SUCCESS": "false"}):
            self.assertFalse(server._setting_bool("notify_on_success", True))
        with mock.patch.dict(server.os.environ, {"NOTIFY_ON_SUCCESS": "true"}):
            self.assertTrue(server._setting_bool("notify_on_success", True))


if __name__ == "__main__":
    unittest.main(verbosity=2)

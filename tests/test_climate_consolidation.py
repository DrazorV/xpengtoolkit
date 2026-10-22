"""Fan and defrost use one climate entity without changing vehicle encodings."""

from enum import IntFlag
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_consolidated_controls import (
    Error,
    VIN,
    coordinator,
    entry,
    layout,
    load,
    module,
    policy,
    state,
)


class Features(IntFlag):
    TARGET_TEMPERATURE = 1
    TURN_ON = 2
    TURN_OFF = 4
    FAN_MODE = 8
    PRESET_MODE = 16


module(
    "homeassistant.components.climate",
    ATTR_TEMPERATURE="temperature",
    ClimateEntity=type("ClimateEntity", (), {}),
    ClimateEntityFeature=Features,
    HVACAction=SimpleNamespace(
        OFF="off", IDLE="idle", HEATING="heating", COOLING="cooling"
    ),
    HVACMode=SimpleNamespace(OFF="off", HEAT_COOL="heat_cool"),
)
module("homeassistant.components.climate.const", PRESET_NONE="none")
module("homeassistant.const", UnitOfTemperature=SimpleNamespace(CELSIUS="C"))
sys.modules["homeassistant.exceptions"].ServiceValidationError = Error
climate = load("custom_components.xpeng.climate", "climate.py")


class ClimateTests(unittest.IsolatedAsyncioTestCase):
    def make(self, p=None):
        send = Mock(return_value=True)
        c = coordinator(state(hvac={"hvac_wind_speed": 3, "hvac_defrost": 0}), p)
        return climate.XPengClimate(c, SimpleNamespace(send_command=send)), send

    async def test_fan_command_and_reported_state(self):
        e, send = self.make()
        self.assertEqual(e.fan_mode, "3")
        await e.async_set_fan_mode("8")
        send.assert_called_once_with(VIN, 3, {"cmd_type": 2, "cmd_value": 8})
        self.assertEqual(e.fan_mode, "3")
        e.coordinator.data = state(hvac={"hvac_wind_speed": 8})
        self.assertEqual(e.fan_mode, "8")
        self.assertEqual(e._attr_fan_modes, [str(n) for n in range(1, 9)])

    async def test_defrost_presets_preserve_existing_commands(self):
        e, send = self.make()
        self.assertEqual(e.preset_mode, "none")
        await e.async_set_preset_mode("defrost")
        send.assert_called_with(VIN, 3, {"cmd_type": 4, "cmd_value": 1})
        self.assertEqual(e.preset_mode, "none")
        e.coordinator.data = state(hvac={"hvac_defrost": 1})
        self.assertEqual(e.preset_mode, "defrost")
        await e.async_set_preset_mode("none")
        send.assert_called_with(VIN, 3, {"cmd_type": 4, "cmd_value": 0})

    async def test_invalid_modes_do_not_publish(self):
        e, send = self.make()
        for val in ("0", "9", "bad"):
            with self.assertRaises(Error):
                await e.async_set_fan_mode(val)
        with self.assertRaises(Error):
            await e.async_set_preset_mode("eco")
        send.assert_not_called()

    async def test_read_only_and_publish_failure(self):
        e, send = self.make(policy.CommandPolicy.from_preset("read_only"))
        self.assertEqual(e.supported_features, 0)
        with self.assertRaises(Error):
            await e.async_set_fan_mode("3")
        with self.assertRaises(Error):
            await e.async_set_preset_mode("defrost")
        send.assert_not_called()
        e.coordinator.command_policy = policy.CommandPolicy.from_preset("full")
        send.return_value = False
        with self.assertRaises(Error) as exc:
            await e.async_set_fan_mode("3")
        self.assertEqual(exc.exception.key, "command_not_sent")

    def test_missing_and_unsupported_feedback_stay_unknown(self):
        e, _ = self.make()
        for v in (None, 0, 9, "bad", float("nan")):
            e.coordinator.data = state(hvac={"hvac_wind_speed": v, "hvac_defrost": -1})
            self.assertIsNone(e.fan_mode)
            self.assertIsNone(e.preset_mode)

    def test_compact_layout_folds_controls_and_raw_duplicates_into_climate(self):
        p = policy.CommandPolicy.from_preset("full")
        for domain, key in [
            ("number", "fan_speed_control"),
            ("switch", "defrost_switch"),
            ("sensor", "hvac_fan_speed"),
            ("binary_sensor", "defrost"),
        ]:
            self.assertEqual(
                layout.REPLACEMENTS[(domain, key)][:2], ("climate", "cabin_climate")
            )
            self.assertFalse(layout.include_legacy_entity(entry(), p, domain, key))
            self.assertTrue(layout.include_legacy_entity(entry(True), p, domain, key))


if __name__ == "__main__":
    unittest.main()

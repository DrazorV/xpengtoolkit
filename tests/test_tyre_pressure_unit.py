#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The tyre-pressure display option: one default for four sensors, Home Assistant converts.

Home Assistant already converts a pressure sensor's display unit and lets the user
pick kPa/psi/bar per entity; that per-entity choice is stored in the entity registry
and wins over anything the integration suggests. This option only removes the
busywork of editing four tyres by hand, so the contract is:

1. the stored value maps to a Home Assistant *suggested* unit, or to nothing (the
   unit system decides);
2. an unknown or empty value falls back to "nothing" rather than breaking setup;
3. the option reaches the options form and the four sensors set the attribute;
4. every language carries the two new strings.

The mapping is pure (`display_units.py`), so it is tested directly; the wiring is
checked structurally, the same way the config-flow tests pin the rest of the form.

    python3 tests/test_tyre_pressure_unit.py
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _component  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "display_units", _component.module_path("display_units.py"))
assert _spec and _spec.loader
display = importlib.util.module_from_spec(_spec)
sys.modules["display_units"] = display
_spec.loader.exec_module(display)

CONFIG_FLOW = (_component.component_dir() / "config_flow.py").read_text(encoding="utf-8")
SENSOR = (_component.component_dir() / "sensor.py").read_text(encoding="utf-8")
TRANSLATIONS = _component.component_dir() / "translations"


class TestMapping(unittest.TestCase):
    def test_system_means_no_suggestion(self):
        self.assertIsNone(display.suggested_tyre_pressure_unit("system"))
        self.assertIsNone(display.suggested_tyre_pressure_unit(""))

    def test_the_three_units_pass_through(self):
        for unit in ("kPa", "psi", "bar"):
            self.assertEqual(display.suggested_tyre_pressure_unit(unit), unit)

    def test_surrounding_whitespace_is_tolerated(self):
        self.assertEqual(display.suggested_tyre_pressure_unit(" psi "), "psi")

    def test_an_unknown_value_falls_back_to_the_unit_system(self):
        """A hand-edited entry or a future value must not take entity setup down."""
        for value in (None, "Pa", "kpa", "PSI", 3, ["bar"]):
            with self.subTest(value=value):
                self.assertIsNone(display.suggested_tyre_pressure_unit(value))

    def test_only_units_home_assistant_can_convert_from_kpa_are_offered(self):
        # HA's pressure device-class table covers all three, so the conversion is
        # HA's - the integration never converts a value itself.
        self.assertEqual(set(display.TYRE_PRESSURE_UNITS), {"kPa", "psi", "bar"})

    def test_the_form_choices_match_the_mapping(self):
        values = [option["value"] for option in display.TYRE_PRESSURE_UNIT_OPTIONS]
        self.assertEqual(values, ["system", "kPa", "psi", "bar"])
        self.assertEqual(values[0], display.DEFAULT_TYRE_PRESSURE_UNIT)
        for option in display.TYRE_PRESSURE_UNIT_OPTIONS:
            self.assertTrue(option["label"])


class TestWiring(unittest.TestCase):
    def test_the_options_form_offers_it(self):
        self.assertIn("CONF_TYRE_PRESSURE_UNIT,", CONFIG_FLOW)
        self.assertIn("TYRE_PRESSURE_UNIT_OPTIONS", CONFIG_FLOW)
        self.assertIn("SelectSelectorConfig(", CONFIG_FLOW)

    def test_the_sensor_platform_reads_the_option(self):
        self.assertIn("suggested_tyre_pressure_unit(", SENSOR)
        self.assertIn("entry.options.get(CONF_TYRE_PRESSURE_UNIT)", SENSOR)

    def test_only_the_tyre_sensors_get_the_suggestion(self):
        self.assertIn('description.key.startswith("tyre_pressure_")', SENSOR)
        self.assertIn("self._attr_suggested_unit_of_measurement = tyre_pressure_unit", SENSOR)

    def test_the_entity_description_keeps_kpa_as_the_native_unit(self):
        const = (_component.component_dir() / "const.py").read_text(encoding="utf-8")
        start = const.index('key="tyre_pressure_fl"')
        block = const[start:const.index('key="tyre_pressure_rr"', start) + 200]
        self.assertIn("native_unit_of_measurement=UnitOfPressure.KPA", block)


class TestTranslationsCarryIt(unittest.TestCase):
    def test_every_language_has_both_keys(self):
        for path in sorted(TRANSLATIONS.glob("*.json")):
            if path.stem in {"strings"}:
                continue
            with self.subTest(language=path.stem):
                data = json.loads(path.read_text(encoding="utf-8"))
                init = data["options"]["step"]["init"]
                self.assertIn("tyre_pressure_unit", init["data"])
                self.assertIn("tyre_pressure_unit", init["data_description"])
                self.assertTrue(init["data"]["tyre_pressure_unit"])
                self.assertTrue(init["data_description"]["tyre_pressure_unit"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

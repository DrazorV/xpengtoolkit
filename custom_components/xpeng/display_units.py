"""Display-unit choices that are integration options, not unit-system settings.

Home Assistant already converts a sensor's display unit natively: a pressure
sensor with a native unit of kPa can be shown in kPa, psi, bar, hPa and the rest,
and a unit picked in an entity's own settings is stored in the entity registry and
wins over anything the integration suggests. That per-entity setting is the right
place for a one-off; changing four tyre-pressure sensors by hand is busywork, so
the integration offers one option for the *default*.

This module holds only the policy (the stored value and the mapping to Home
Assistant's ``suggested_unit_of_measurement``) with no Home Assistant imports, so
it can be tested on its own; the wiring lives in ``config_flow.py`` and
``sensor.py``.
"""
from __future__ import annotations

from typing import Any, Final

#: The config-entry option that holds the choice.
CONF_TYRE_PRESSURE_UNIT: Final = "tyre_pressure_unit"

#: "system" means "do not suggest a unit": Home Assistant's unit system decides.
TYRE_PRESSURE_UNIT_SYSTEM: Final = "system"

#: The units this option can pin the four sensors to. All three are in Home
#: Assistant's pressure device-class unit table, so the conversion is HA's.
TYRE_PRESSURE_UNITS: Final = ("kPa", "psi", "bar")

DEFAULT_TYRE_PRESSURE_UNIT: Final = TYRE_PRESSURE_UNIT_SYSTEM

#: The options-form dropdown. Labels are literal, like this form's other
#: selectors; the units are language-neutral and only the first phrase is
#: English, matching the form's existing hardcoded labels.
TYRE_PRESSURE_UNIT_OPTIONS: Final = (
    {"value": TYRE_PRESSURE_UNIT_SYSTEM, "label": "Home Assistant unit system"},
    {"value": "kPa", "label": "kPa"},
    {"value": "psi", "label": "psi"},
    {"value": "bar", "label": "bar"},
)


def suggested_tyre_pressure_unit(value: Any) -> str | None:
    """Map the stored option to HA's suggested unit, or None for the unit system.

    Returns None for "system" (the default), for an empty value and for anything
    unexpected - a hand-edited entry or a value from a future version must not
    take entity setup down, and Home Assistant's own conversion is the safe
    fallback.
    """
    unit = str(value or "").strip()
    return unit if unit in TYRE_PRESSURE_UNITS else None

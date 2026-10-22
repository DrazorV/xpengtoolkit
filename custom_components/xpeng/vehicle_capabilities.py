"""Conservative feature support from the app's software/hardware/model sources.

Missing fields are unknown, never a reason to hide a control. These are feature
gates, not readiness checks: a sleeping car or an unplugged cable has the same
capabilities as an awake, plugged-in car.
"""

from __future__ import annotations

from typing import Any
from .model_features import MODEL_FEATURES

HARDWARE_KEYS = frozenset(
    {
        "AVM",
        "BIG_CUSTOMER",
        "WHEEL_HEAT",
        "WHEEL_HEAT_DM",
        "FRIDGE",
        "PANORAMIC_SKY_LIGHT",
        "SUN_SHADE",
        "REAR_SEAT_WIND",
        "DRIVER_SEAT_HEAT",
        "PASSENGER_SEAT_HEAT",
        "DRIVER_SEAT_WIND",
        "PASSENGER_SEAT_WIND",
        "REAR_SEAT_HEAT",
        "ELECTRIC_TAIL",
        "DRIVER_SEAT_HEAT_HARDWARE",
        "PASSENGER_SEAT_HEAT_HARDWARE",
        "DRIVER_SEAT_WIND_HARDWARE",
        "PASSENGER_SEAT_WIND_HARDWARE",
        "REAR_SEAT_HEAT_HARDWARE",
        "HVAC_SFS",
        "FRONT_MIRROR_HEAT",
        "BONNET_UNLOCK",
        "TRAILER_HOOK",
        "SCISSORS_DOOR",
        "ELECTRIC_DOOR",
        "THIRD_ROW_LEFT_SEAT_HEAT",
        "THIRD_ROW_RIGHT_SEAT_HEAT",
        "THIRD_ROW_MIDDLE_SEAT_HEAT",
    }
)
LOCAL_KEYS = frozenset(
    {
        "isSupportAcAutoMode",
        "isSupportChargePortControl",
        "isSupportOneChargePort",
        "isSeatDoubleCheck",
        "isSupportSeatFrontHeat",
        "isSupportSeatFrontWind",
        "isSupportSeatBackHeat",
        "isSupportSeatBackWind",
        "isSupportAirClean",
        "isSupportFrontDeforest",
        "isSupportRearDeforest",
        "isSupportAirDeodorization",
        "isSupportAirHighTemp",
        "isSupportDischargeCard",
        "isSupportFastCold",
        "isSupportFastWarm",
        "isSupportSilentMode",
        "isSupportTrailerHook",
    }
)


def flag(value: Any) -> bool | None:
    """Accept only explicit API booleans; 'false' must never become truthy."""
    if type(value) is bool:
        return value
    if type(value) is int and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        return {"true": True, "false": False, "1": True, "0": False}.get(value.lower())
    return None


def normalize_flags(data: Any, keys: frozenset[str]) -> dict[str, bool]:
    """Retain only known feature booleans, excluding identifiers and credentials."""
    if not isinstance(data, dict):
        return {}
    return {key: parsed for key in keys if (parsed := flag(data.get(key))) is not None}


def _any(*values: bool | None) -> bool | None:
    if True in values:
        return True
    return False if all(v is False for v in values) else None


def _all(*values: bool | None) -> bool | None:
    if False in values:
        return False
    return True if all(v is True for v in values) else None


class VehicleCapabilities:
    """Tri-state decisions: True supported, False unsupported, None unknown."""

    def __init__(self, software=None, hardware=None, local=None):
        caps = software.get("capabilities") if isinstance(software, dict) else software
        self.software = (
            set(caps)
            if isinstance(caps, list) and caps and all(isinstance(c, str) for c in caps)
            else None
        )
        self.hardware = normalize_flags(hardware, HARDWARE_KEYS)
        self.local = normalize_flags(local, LOCAL_KEYS)

    def software_flag(self, key: str) -> bool | None:
        return key in self.software if self.software is not None else None

    def support(self, feature: str) -> bool | None:
        h, l, s = self.hardware.get, self.local.get, self.software_flag
        if feature == "charge_port_control":
            return l("isSupportChargePortControl")
        if feature == "rear_seat_ventilation":
            return _any(l("isSupportSeatBackWind"), h("REAR_SEAT_WIND"))
        if feature == "steering_wheel_heat":
            hw = _any(h("WHEEL_HEAT"), h("WHEEL_HEAT_DM"))
            return (
                hw if hw is not None else (True if s("STEERING_WHEEL_HEAT") else None)
            )
        if feature == "sentinel":
            big_customer = h("BIG_CUSTOMER")
            return _all(
                s("SENTINEL_MODE"),
                h("AVM"),
                None if big_customer is None else not big_customer,
            )
        if feature in SEAT_FEATURES:
            software, hardware, local = SEAT_FEATURES[feature]
            legacy = _any(l(local), h(hardware))
            newer = _all(s(software), h(hardware + "_HARDWARE"))
            double_check = l("isSeatDoubleCheck")
            if double_check is not None:
                return newer if double_check else legacy
            # The app has two seat-gating paths. Without knowing which applies,
            # hide only when both paths agree; a positive software flag alone
            # is insufficient to claim that optional hardware exists.
            return legacy if legacy is newer else None
        if feature == "fridge":
            return _all(s("FRIDGE_SOFTWARE"), h("FRIDGE"))
        if feature == "sun_shade":
            return _all(s("SUN_SHADE_SOFTWARE"), h("SUN_SHADE"))
        if feature == "sky_sun_shade":
            return _all(s("SUN_SHADE_SOFTWARE"), h("PANORAMIC_SKY_LIGHT"))
        if feature == "battery_warm":
            return s("CHARGE_BATTERY_KEEP_WARM")
        if feature == "charge_schedule":
            return s("CHARGE_MANAGE_SOFTWARE")
        return None

    def decisions(self) -> dict[str, str]:
        return {
            key: {True: "supported", False: "unsupported", None: "unknown"}[
                self.support(key)
            ]
            for key in FEATURES
        }


SEAT_FEATURES = {
    "driver_seat_heat": (
        "DRIVER_SEAT_HEAT_SOFTWARE",
        "DRIVER_SEAT_HEAT",
        "isSupportSeatFrontHeat",
    ),
    "passenger_seat_heat": (
        "PASSENGER_SEAT_HEAT_SOFTWARE",
        "PASSENGER_SEAT_HEAT",
        "isSupportSeatFrontHeat",
    ),
    "driver_seat_ventilation": (
        "DRIVER_SEAT_WIND_SOFTWARE",
        "DRIVER_SEAT_WIND",
        "isSupportSeatFrontWind",
    ),
    "passenger_seat_ventilation": (
        "PASSENGER_SEAT_WIND_SOFTWARE",
        "PASSENGER_SEAT_WIND",
        "isSupportSeatFrontWind",
    ),
    "rear_seat_heat": (
        "REAR_SEAT_HEAT_SOFTWARE",
        "REAR_SEAT_HEAT",
        "isSupportSeatBackHeat",
    ),
}
FEATURES = (
    *SEAT_FEATURES,
    "rear_seat_ventilation",
    "steering_wheel_heat",
    "sentinel",
    "charge_port_control",
    "fridge",
    "sun_shade",
    "sky_sun_shade",
    "battery_warm",
    "charge_schedule",
)

# Existing entity suffixes remain unchanged. Optional controls and their old
# duplicate sensors share a gate; unrelated telemetry is never suppressed.
ENTITY_FEATURES = {
    "steering_wheel_heat_select": "steering_wheel_heat",
    "steering_wheel_heat": "steering_wheel_heat",
    "sentinel_switch": "sentinel",
    "sentinel_sensitivity_control": "sentinel",
    "sentinel_mode": "sentinel",
    "sentinel_sensitivity": "sentinel",
    "query_xguard": "sentinel",
    "open_charge_port": "charge_port_control",
    "close_charge_port": "charge_port_control",
}
for _prefix, _feature in (
    ("driver_seat_heat", "driver_seat_heat"),
    ("passenger_seat_heat", "passenger_seat_heat"),
    ("driver_seat_ventilation", "driver_seat_ventilation"),
    ("passenger_seat_ventilation", "passenger_seat_ventilation"),
    ("left_rear_seat_heat", "rear_seat_heat"),
    ("right_rear_seat_heat", "rear_seat_heat"),
    ("left_rear_seat_ventilation", "rear_seat_ventilation"),
    ("right_rear_seat_ventilation", "rear_seat_ventilation"),
):
    ENTITY_FEATURES[_prefix] = _feature
    ENTITY_FEATURES[_prefix + "_select"] = _feature


def model_flags(vehicle_type: str | None, vehicle_name: str | None) -> dict[str, bool]:
    """Explicit app 3.12.0 model facts; no fallback assumptions for unknown models."""
    profile = MODEL_FEATURES.get(vehicle_type, {})
    return {**profile.get(vehicle_type, {}), **profile.get(vehicle_name, {})}


def from_coordinator(coordinator) -> VehicleCapabilities:
    local = model_flags(
        getattr(coordinator, "vehicle_type_code", None),
        getattr(coordinator, "vehicle_type_name", None),
    )
    local.update(getattr(coordinator, "vehicle_local_config", None) or {})
    return VehicleCapabilities(
        getattr(coordinator, "remote_capabilities", None),
        getattr(coordinator, "vehicle_hardware", None),
        local,
    )

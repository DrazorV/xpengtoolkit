"""The tracker's map-card contract: ``course`` must come from the car's own angle.

Home Assistant's map card rotates the vehicle marker from ``course``. The tracker
exposed the angle only as a ``bearing`` extra attribute, so the marker always pointed
north; a number that the car never sent must stay None rather than defaulting to 0.
"""
from __future__ import annotations

import ast
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _component  # noqa: E402

TREE = ast.parse(
    (_component.component_dir() / "device_tracker.py").read_text(encoding="utf-8")
)
TRACKER = next(
    node
    for node in TREE.body
    if isinstance(node, ast.ClassDef) and node.name == "XPengDeviceTracker"
)


def _properties(*names):
    """Execute the real property bodies without importing Home Assistant."""
    nodes = [
        node
        for node in TRACKER.body
        if isinstance(node, ast.FunctionDef) and node.name in names
    ]
    module = ast.Module(
        body=[
            ast.ImportFrom(
                module="__future__",
                names=[ast.alias(name="annotations")],
                level=0,
            ),
            *nodes,
        ],
        type_ignores=[],
    )
    namespace: dict = {}
    exec(compile(ast.fix_missing_locations(module), "<device_tracker>", "exec"), namespace)
    return namespace


class CourseTests(unittest.TestCase):
    def _course(self, angle):
        getter = _properties("course")["course"]
        self.assertIsInstance(getter, property)
        requested = []

        class Stub:
            def _get_nested_value(self, path):
                requested.append(path)
                return angle

        value = getter.fget(Stub())
        self.assertEqual(requested, ["msg_content.interval.drive.angle"])
        return value

    def test_the_angle_becomes_a_float_course(self):
        self.assertEqual(self._course(90), 90.0)
        self.assertEqual(self._course(186.4), 186.4)

    def test_no_angle_is_none_not_zero(self):
        """0 degrees is north: a car that sent nothing must not point there."""
        self.assertIsNone(self._course(None))

    def test_a_malformed_angle_does_not_raise(self):
        for bad in ("north", {}, []):
            self.assertIsNone(self._course(bad), bad)


if __name__ == "__main__":
    unittest.main(verbosity=2)

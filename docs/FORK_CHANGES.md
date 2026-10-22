# Fork development

Upstream baseline: 0.6.20 (dc0134c). Domain and entity identifiers remain compatible.

## Development and review

Install requirements-test.txt and run `python3 tools/run_tests.py`. Every standalone
suite runs in its own Python process so Home Assistant stubs cannot leak between suites.
GitHub Actions runs the same command on pull requests and main.

Test-harness repairs load the standard-library calendar before component-path imports,
provide the missing entity-registry stub and preserve annotation names when compiling
an extracted coordinator method. Production behavior is unchanged by these repairs.

Raw vehicle recordings, account tokens and certificates remain local. New protocol
behavior must be backed by a sanitized regression fixture and a recorded physical
vehicle test before it is described as verified on that model.

## 0.6.21 — initial telemetry and command feedback fixes

- Accept useful first partial MQTT state without requiring an ext block. Empty
  acknowledgements remain ignored and the replay guard still decides acceptance.
- Merge successive partial sections without dropping earlier fields, and keep
  the accepted merged baseline for the next message.
- Return unknown for enum values that Home Assistant cannot represent, including
  the charge-port sentinel that previously raised an entity update exception.
- Reject invalid seat choices instead of silently sending Off. Report failed
  MQTT publication immediately and stop the remaining command sequence.
- Display command responses in English while preserving the original response
  message, code and recent payloads in diagnostic attributes.

Seat encoding and the measured off-first sequence are unchanged. A successful
publication is not physical confirmation. Passenger-seat Off and model-specific
seat behavior still require an observed P7+ test; this release does not claim
those protocol questions are solved. Telemetry regression fixtures describe
supported message shapes and are synthetic, not recordings from the user's car.


## 0.7.0 — consolidated controllers

New installations use the compact entity layout. Trunk, windows and charge port
use native Home Assistant covers; charging start/stop and measured activity use
one charging switch. Covers preserve the access/securing distinction: permission
to close never implies permission to open. They wait for telemetry rather than
claiming a physical state change after publication. No movement, stop or arbitrary
position support is fabricated.

Identical sensor state is folded into its existing number, select, switch, lock
or climate entity. Detailed charging state, cable presence, cabin measurements,
individual doors and separate heating/ventilation functions remain distinct.
When the replacement's command capability is disabled, its raw state sensor is
retained. Existing control unique IDs are preserved.

Existing entries migrate with **Keep legacy buttons and duplicate sensors** on.
This preserves existing automations. Owners can turn it off after updating their
consumers. Compact setup removes only the integration's explicitly superseded
registry entries; Home Assistant retains deleted-entry metadata and history.
The new covers/switch inherit the former primary state's renamed object ID,
area, labels, aliases and name/icon overrides, without overwriting an existing
controller's customizations. Turning legacy entities back on restores those IDs
through Home Assistant's registry recovery while that metadata is retained.

Vehicle evidence supplied by a P7+ owner on 2026-10-22:

- Trunk open and close commands work. Their encodings are unchanged.
- The existing open-windows command (`12`, `cmd_type=1`, `cmd_value=2`)
  **vents** the windows. The new window cover opens to that ventilation position.
  It does not advertise full opening, exact target positions or a close command.
- Old close/vent payloads were identical to the charge-port payloads and did not
  control the windows. Legacy window-close actions now fail clearly without
  publishing. Ventilation uses the observed working command. Closing windows
  requires the XPENG app or vehicle until a supported command is captured; no
  guessed numeric command is sent to a vehicle.
- Charge-port control did not work on that P7+. Owners of manual/non-remote flaps
  can turn off **Motorized charge-port controls**. The cover continues reporting
  its state without open/close actions. Other cars retain the prior motorized
  commands, with no new claim of physical compatibility.

This is an integration change, not a set of per-installation template helpers.

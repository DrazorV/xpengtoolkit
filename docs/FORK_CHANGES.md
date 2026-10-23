# Fork development

Upstream baseline: 0.6.25 (321460b). Domain and entity identifiers remain compatible.

## 0.6.26 - upstream review fixes

Merged the reviewed contribution from upstream PR
[xpengtoolkit/xpengtoolkit#5](https://github.com/xpengtoolkit/xpengtoolkit/pull/5),
commit `f7f8233`, together with upstream 0.6.25's parked SOC/baseline fix.
The upstream PR remains open for maintainer review; inclusion here does not mean
upstream approval. The merge retains both repositories' ancestry.

- Correlate command acknowledgements with request identity and confirm legacy
  window, charging, charge-port, charge-limit and front-defrost command paths.
- Keep raw fan telemetry in compact mode and propagate measured command state
  into the MQTT baseline without advancing snapshot freshness.
- Make dashboard-card registration an explicit, default-off vehicle option with
  shared-resource cleanup. Existing card users must enable **Install and manage
  the XPENG Vehicle dashboard card** under the integration's Configure options
  after upgrading; their dashboard card configuration is preserved.
- Make standard unittest discovery safe and run it in CI, alongside isolated
  regression scripts and card tests. Update permission/targeting docs, dependency
  bounds and SHA-pinned action references.

Fork publishing settings, issue links, card behavior and provenance notes are
preserved. No new command encoding or additional physical vehicle validation is
claimed. See [upgrade and downgrade notes](RELEASE_NOTES_0.6.26.md).

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


## 0.7.1 — one climate controller

Compact mode also folds the fan-speed number and front-defrost switch into the
climate entity. Fan modes 1–8 use the existing service-3, cmd-type-2 command;
the defrost/none presets use the existing cmd-type-4 command. Both report measured
telemetry, reject invalid choices and surface publication failure. Read-only mode
withdraws all climate features and direct calls remain guarded. Legacy mode keeps
the old fan/defrost entities; the expected full compact count is now 101.


## 0.7.2 — window closing, charging feedback and feature discovery

The window cover and legacy window-close service/button use the official
Android app's service 12, cmd_type 1, cmd_value 1. Opening remains ventilation,
not full opening. A P7+ owner physically confirmed ventilation and closing
using the 0.7.2b1 integration build on 22 October 2026.
Successful window responses update measured positions without advancing the
full-state freshness clock or fabricating motion.

Covers and the charging switch wait for a vehicle acknowledgement. A rejection,
timeout or malformed reply raises a translated error. Rejection 10401 identifies
a charging-start failure and suggests checking the cable and charging station.
The existing charging start/stop encodings are unchanged. Charging state and
cable presence are exposed on the switch.

Feature discovery combines software flags, allowlisted hardware booleans,
explicit model facts and a read-only cloud model overlay. Known unsupported
seat/sentinel controls are disabled through the registry; existing IDs/history
and user/config-entry disabling remain intact. Integration-disabled optional
controls become enabled when support is known. Manual charge flaps keep their
cover state without motor actions. Missing/failed discovery is unknown; charger
readiness and rejection codes are never used as permanent capability evidence.

See [the derived command inventory](COMMAND_RESEARCH.md) for 97 app MQTT handler
actions, source limitations and unresolved operations. It does not expose new
untested operations as controls. The renewal app's shared error module is synced;
the renewal app version and credential handling are unchanged.

Upstream 0.6.22 history is merged through PR #6. PR #7 preserves evcc interfaces,
including the old climate binary sensor, in compact mode.


## 0.7.3 — verified climate power and temperature

Climate power and target temperature now follow the official app's distinct
commands and vehicle capability flags. The previous target payload used the
quick-cooling command, producing rejection code 8. Fractional temperature and
optional duration follow the reported capabilities; integer-only cars use the
integer-temperature command. Native temperature changes do not power on A/C;
the explicit climate-on service sets its target before starting.

The P7+ owner physically confirmed power on, power off and a 22 C target with
0.7.3b1 on 22 October 2026. Rejections and timeouts now raise errors, and measured
HVAC responses update state without optimistic success or a false full-snapshot
timestamp. Existing entity IDs and evcc interfaces are preserved.

The old fan-speed mapping sent the integer-temperature command. Climate no
longer advertises fan control and the legacy number refuses that payload until
a valid remote fan command is identified. This corrects the 0.7.1 fan claim;
raw fan telemetry remains available. Other models and climate actions still
require physical validation. No app sources, captures or credentials are included.


## 0.7.4b1 — app climate modes and schedule management (test build)

Adds seven independent, capability-gated measured switches: maximum heating,
maximum cooling, Refresh, Sterilisation, A/C cleaning, rear defrost and Pet mode.
Each combines on/off in one entity. Pet telemetry's checking state is preserved
as unknown; command acknowledgements do not create optimistic success.
Vehicle-scoped schedule actions now surface errors and refresh measured state.
The companion reusable card 0.1.4 adds the mode grid and schedule editor.

The owner's app resources and SDK establish the mappings. Physical validation
of these new switches through Home Assistant remains pending. The 0.7.3
on/off and 22 C validation still applies. Existing unique IDs, evcc interfaces,
credential handling and the renewal app version are unchanged.


## 0.7.5 — bundled dashboard card

- Ship the existing card 0.1.6 inside the HACS integration directory. The card
  source has one canonical copy in `custom_components/xpeng/www/`; its isolated
  JavaScript tests remain in `lovelace/xpeng-vehicle-card/`.
- Register its static file and module resource automatically at integration
  setup. Hash the shipped asset in an executor to refresh browser caches on
  updates; register only once for multiple vehicles and integration reloads.
- Migrate the exact legacy local resource URL in place, preserving its ID and
  dashboard configurations. Remove duplicate registrations of this card only.
  YAML-managed resources load through the frontend API without rewriting YAML.
- Frontend failures are logged without preventing vehicle setup. Headless
  installations skip card registration. Minimum Home Assistant is 2024.7 for
  its asynchronous static-path registration API.
- Vehicle commands, entity IDs, evcc interfaces and card behavior are unchanged,
  including mandatory trunk-open confirmation and immediate closing.


## 0.7.6 — parking-light card default

Card 0.1.7 displays parking lights as Off when their switch state is unknown,
including the compact tile, panel heading and selected Off action. Reported
On/Off states take precedence. Missing or unavailable controls retain their
existing behavior. This is a display default only; it does not fabricate entity
telemetry or send any command. The bundled resource hash updates automatically.

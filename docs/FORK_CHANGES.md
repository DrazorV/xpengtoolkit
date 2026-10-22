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

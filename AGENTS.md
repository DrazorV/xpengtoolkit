# Development notes for DrazorV/xpengtoolkit

This is DrazorV's development fork of xpengtoolkit/xpengtoolkit. The user has
authorized publishing fixes, PRs and releases to this fork. Publish as DrazorV;
the upstream maintainer's machine-specific xpengtoolkit identity rule does not
apply to this fork. Never push to the upstream remote without a separate request.

- Use codex/ branches and PRs targeting this fork's main branch.
- Run `python3 tools/run_tests.py` before merging. Tests run in separate processes.
- Test dependencies: `python3 -m pip install -r requirements-test.txt`.
- Preserve domain xpeng, existing unique IDs and config-entry compatibility.
- Never commit credentials, certificates, captured vehicle traffic or local IDE metadata.
- Preserve the original MIT notice and record upstream provenance.
- The integration and credential renewal app are versioned independently. Integration
  releases must match custom_components/xpeng/manifest.json. Do not change the
  renewal app's vendored copy without tools/sync_renew_vendor.py and its tests.
- Changes to command encodings require vehicle evidence. A successful publish or
  acknowledgement is not confirmation that a physical setting changed.

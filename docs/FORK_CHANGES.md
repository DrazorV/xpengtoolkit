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

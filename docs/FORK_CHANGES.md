# Fork changes and upstream synchronization

This fork follows [xpengtoolkit/xpengtoolkit](https://github.com/xpengtoolkit/xpengtoolkit).
The current baseline is upstream commit `4ce26a5`, release **0.6.34**.

The command/control work and optional card were accepted upstream in
[PR #5](https://github.com/xpengtoolkit/xpengtoolkit/pull/5), the Android command
audit in [PR #7](https://github.com/xpengtoolkit/xpengtoolkit/pull/7), and card
number formatting in [PR #15](https://github.com/xpengtoolkit/xpengtoolkit/pull/15).
Those changes now come from upstream's own commits rather than duplicate fork
commits.

The only pending integration behavior change is the startup I/O and watchdog
diagnostics fix in [PR #16](https://github.com/xpengtoolkit/xpengtoolkit/pull/16).
Main retains that fix together with fork-specific publishing configuration in
one consolidated commit on the upstream baseline. The upstream PR has its own
clean branch and does not include fork metadata.

Fork configuration includes the DrazorV publishing instructions, README banner,
issue-tracker URL, development ignores, this provenance note, and published
integration version 0.6.35. The renewal-image workflow lowercases the repository
owner for GHCR, with its regression test and documentation. The renewal app is
versioned independently. Original MIT notices, credentials compatibility and
Home Assistant entity IDs are preserved.

At the owner's request, main was rebuilt on 29 October 2026. Its previous tip,
`73252b6`, and complete ancestry are recoverable under
`archive/main-before-upstream-sync-20261029`. The earlier archive
`archive/main-before-upstream-sync-20261024` also remains. Existing release tags
are never moved; release 0.6.35 still identifies the original tested release
commit. Vendored file modes now match upstream; their contents are unchanged.

For future synchronization, fetch upstream and inspect both ancestry and actual
file differences. Keep a single consolidated fork patch on current upstream;
drop fixes from that patch once upstream accepts them. Do not accumulate merge
commits for changes upstream has squash-merged under other commit IDs. Before
any requested history realignment, preserve the old tip remotely, verify the
resulting tree and use an explicit expected old SHA when updating main. Preserve
open upstream PR branches and published release tags.

Install requirements-test.txt, then run `python3 tools/run_tests.py`,
`python3 -m unittest discover -s tests` and the reusable vehicle-card tests before
publishing integration changes.

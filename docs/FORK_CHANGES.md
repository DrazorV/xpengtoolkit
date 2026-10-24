# Fork changes and upstream synchronization

This fork follows [xpengtoolkit/xpengtoolkit](https://github.com/xpengtoolkit/xpengtoolkit).
The current baseline is upstream commit `e0b7147`, including release **0.6.27**
and the vehicle-card tutorial.

Our command corrections, native controls, climate modes, evcc compatibility and
optional vehicle card were accepted upstream in
[PR #5](https://github.com/xpengtoolkit/xpengtoolkit/pull/5), commit `652d3a2`.
Those features now come directly from upstream. Integration runtime code is
identical to this baseline except for the issue-tracker URL in manifest.json.

The remaining fork changes are publishing instructions, local development ignore
patterns, the README fork banner, this provenance note and the fork issue link.
The original MIT notice and Home Assistant entity identifiers are preserved.

At the owner's request, main was rebuilt from upstream plus one fork-metadata
commit on 24 October 2026. Previous fork main and its complete history are kept
under tag `archive/main-before-upstream-sync-20261024`; existing release tags
are unchanged. Historical fork validation notes are available at that tag.

For future updates, merge upstream main to preserve shared ancestry. If upstream
squashes another contribution, align main deliberately with a verified tree and
an archive first; commit counts alone do not describe code differences.

Install requirements-test.txt, then run `python3 tools/run_tests.py`,
`python3 -m unittest discover -s tests` and the reusable vehicle-card tests before
publishing integration updates. The renewal app is versioned independently.

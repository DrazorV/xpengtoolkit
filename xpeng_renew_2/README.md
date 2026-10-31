# XPENG credential renewal (2nd car)

A second slot of [XPENG credential renewal](../xpeng_renew) for a second car on its
own XPENG account (XPENG keeps one active session per account, so two cars need two
accounts).

It is the **same worker and the same published image**, with two defaults changed:

| Setting | This slot | The first slot |
| --- | --- | --- |
| Host port | `8091` | `8090` |
| `pair_dir` | `/config/xpeng-secrets-2` | `/config/xpeng-secrets` |

Give it the second account's `email` and `password`, and leave `entry_id` empty: the
pair's VIN selects its own config entry. `solver_url` and `solver_token` are the same
solver; see the [two cars, two accounts](https://xpengtoolkit.github.io/xpengtoolkit/guide/unattended-renewal#two-cars-two-accounts)
section of the guide.

Do not copy `renew_server.py` or the Dockerfile into this directory. The app pulls
`ghcr.io/xpengtoolkit/xpeng-renew`, published by the `Renewal image` workflow, so
both slots always run the same code. `tests/test_addon_slots.py` fails if the
versions, options or schema drift apart.

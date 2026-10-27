# Notifications

XPENG's notifications do **not** arrive over MQTT and are not pushed to this
integration. They live server-side in the app's **Message Centre**, and this
integration polls that list. A new one appears within `NOTIFICATION_POLL_INTERVAL`
(5 minutes) as two things:

- **`sensor.xpeng_<vehicle>_last_notification`** — a diagnostic sensor whose state
  is the message text
- **`xpeng_notification`** — a bus event, carrying the flattened record

Both are fed by the same code path, so an automation can trigger on either form
without caring where the notification came from.

## Where notifications come from

Two sources feed the sensor and the event, and they are different things:

1. `msg_type=3` frames on the MQTT broker, which also fire the bus event. These are
   rare - and **account-takeover notices are excluded**, see below.
2. The app's server-side **Message Centre**, which the coordinator polls every 5
   minutes. This is where the notifications a user actually sees in the app live —
   X-Combo, sentry and similar — and it carries almost everything in practice.

XPENG does not push these over MQTT and they are not APNs/FCM-only either: the
Message Centre holds them and the app reads them back, which makes them pollable.
That is what `NOTIFICATION_POLL_INTERVAL` drives.

The Message Centre groups messages into categories, and the API returns **one
category per request**. All six are polled, and every message is tagged with the
category it came from, so a single sensor covers everything.

## Account takeover notices

The broker sends an `ACCOUNT_KICK_OFF` notice (`service_type` `17`, code
`4003007` — *"Account logged in on another device, local account logged out"*)
every time the **renewal app logs in**. That login is how the credential pair is
renewed, so on a healthy install it arrives about once every 100 minutes. It is
not a fault and it is not a car notification.

Up to 0.6.14 it was recorded as one, which is why
`sensor.xpeng_<vehicle>_last_notification` kept showing that sentence instead of
the notifications a user cares about. Since 0.6.15 it is tracked where a session
event belongs:

- **`xpeng_account_takeover`** — a bus event carrying the notice
  (`service_type`, `code`, `message`, `msg_id`, `timestamp`, and `raw` — the
  push envelope it arrived in);
- `sensor.xpeng_<vehicle>_polling_status` attributes **`last_takeover_at`** and
  **`account_takeovers`** (count since startup);
- the INFO line the MQTT client logs (`Account signed in elsewhere - expecting a
  credential import`), and the `$client/<clientId>` entry in the listener log if
  the MQTT listener is enabled.

After a takeover the client stays quiet for a grace window instead of treating
refused CONNECTs as an auth failure — it is waiting for the renewal's import, and
reconnects within a few seconds of it. See [Fault finding](./fault-finding).

## The six categories

| Category | Code | Typically holds |
| --- | --- | --- |
| Vehicle Notification | `XPMOBILE-VEH` | X-Combo, sentry, window/door events |
| XPENG Notification | `XPMOBILE-PUS` | Account and system messages |
| Charging Notification | `XPMOBILE-CHA` | Charge start/stop, completion |
| Service Notification | `XPMOBILE-SER` | Servicing and maintenance |
| Order Notification | `XPMOBILE-ORD` | Orders and purchases |
| Event Notification | `XPMOBILE-JOY` | Campaigns and events |

In practice **Vehicle Notification** is the busy one, and the rest are usually
empty — but an empty category and an unqueried category look identical over the
API (both return `[]`), so all six are queried rather than assumed.

## What the sensor carries

The state is the message text of the most recent notification (or `code <n>`, or
`received`, when the record has no message body). The attributes add:

| Attribute | Contents |
| --- | --- |
| `count` | How many new notifications have arrived since startup. It stays at `0` until something new arrives. |
| `recent` | The last five records, each with `title`, `message`, `category`, `msg_type`, `read`, `msg_id`, `timestamp` and that record's `raw`. |
| `raw` | The unparsed record for the latest notification — a Message Centre item, or the MQTT push envelope for a `msg_type=3` push. See [The raw record](#the-raw-record). |
| `timestamp` | When XPENG says the message was created (the Message Centre `createTime`). For a `msg_type=3` push there is no claimed time, so this is when it arrived. |
| `collected_at` | When the poll recorded the message. |
| `delay_s` | `collected_at` minus `timestamp`: the poll interval plus however long the API took, or `0` for a push. Stamped once when the record is collected, so it does not grow as the entity is read. |
| `category`, `title`, `msg_type` | The latest record's classification and display fields, at the top level so a state trigger can filter on them. `None` for a `msg_type=3` push, which is not a Message Centre item. |
| `message`, `source`, `code`, `msg_id` | The flattened fields of the latest record, for convenience. |

The `xpeng_notification` event carries the same flattened record for the
notification that fired it. Human-readable text is extracted from the app's HTML
bodies, so `message` is plain text rather than markup.

### Capture with the event, not the sensor state

An automation that must **record every message** has to trigger on the
`xpeng_notification` event. The sensor's state is the message text, so a second
notification with the same text produces no state change — two identical X-Combo
messages collapse into one. The event fires once per new Message Centre item and
carries the same fields in `trigger.event.data`. A worked example (event trigger
plus a Logbook line that keeps the text) is in
[Capture XPENG notifications](../tutorials/notification-capture).

### The raw record

Both the sensor's `raw` attribute and the event's `raw` field carry the record
exactly as it arrived, before any parsing. A polled notification is a Message
Centre item:

```json
{
  "id": "1558173270679261184",
  "messageId": "1558173270679261184",
  "read": false,
  "createTime": "2026-10-09 09:44:17.0000",
  "messageContent": "{\"msgContent\":{\"title\":\"XCOMBO-...\",\"description\":\"<p>...</p>\"},...}"
}
```

A rare `msg_type=3` push carries the MQTT envelope instead — `msg_type`,
`service_type`, `msg_id` and the nested `msg_content` — because that envelope is
where the extra fields live; the flattened top level is what parsing produced.

`messageContent` is deliberately left as the original JSON *string*, not the
parsed object. That is the point: if XPENG renames or moves a field the parser
reads, the captured `raw` still holds it, so the parser can be fixed from the
event or the entity's attributes instead of needing a new live capture. Nothing
in the integration depends on `raw`'s contents — it exists for that failure mode.

## Triggering automations

Either form works. The event trigger:

```yaml
automation:
  - alias: X-Combo notification
    triggers:
      - trigger: event
        event_type: xpeng_notification
    conditions:
      - condition: template
        value_template: "{{ trigger.event.data.category == 'XPMOBILE-VEH' }}"
    actions:
      - action: notify.persistent_notification
        data:
          message: "{{ trigger.event.data.message }}"
```

or trigger on the sensor's state directly, which is easier to build in the UI:

```yaml
automation:
  - alias: XPENG notification
    triggers:
      - trigger: state
        entity_id: sensor.xpeng_<vehicle>_last_notification
        not_from:
          - unknown
          - unavailable
    actions:
      - action: notify.persistent_notification
        data:
          message: "{{ trigger.to_state.state }}"
```

Both forms carry the same fields now: the event in `trigger.event.data`, the
sensor as top-level attributes. The event is still the one to use for capture,
because it fires once per item even when the text repeats; the sensor's state is
the text, so identical messages produce no state change.

## Only new notifications fire

Two behaviours are worth knowing before you rely on this:

- **Only new notifications fire.** The first poll after a restart records the
  existing inbox as a baseline *without* firing, so a restart does not replay the
  whole Message Centre into your automations. The first poll logs how many entries
  it primed, so that baseline is visible in the log.
- **Anything that arrives while Home Assistant is down is absorbed into that
  baseline** and will not trigger. If you need those, they are still in `recent`
  and the `count` attribute after startup.

## A different certificate authority

Worth knowing if you ever chase a notification problem.
`apps-global.xiaopeng.com` is signed by the XPENG CA chain shipped with this
integration, so that endpoint is verified against the pinned chain alone.

`msgcenter-oversea-eur.xiaopeng.com` is **not** — it sits behind Aliyun's WAF and
serves a public certificate. The integration therefore adds the system CA store
*in addition to* the pinned chain for that endpoint only. Pinning it to the XPENG
chain as well made every message-centre call fail with

```log
SSL: CERTIFICATE_VERIFY_FAILED - unable to get local issuer certificate
```

while the vehicle API kept working, which is a confusing combination to debug.
Verification is not weakened for anything else: `check_hostname` and
`CERT_REQUIRED` still apply, and the XPENG-chain endpoints are still pinned.

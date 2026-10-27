# Capture XPENG notifications

This walkthrough ends with an automation that records **every** XPENG notification
as a Logbook line that contains its text — including two X-Combo messages with the
same text, which the Last-notification sensor cannot tell apart.

It also shows how to read the unparsed record, so a future XPENG field rename can
be diagnosed from Home Assistant instead of a new live capture.

## What you need

- The integration set up and receiving data (a parked car still publishes; see
  [Fault finding](../guide/fault-finding) if the entities are unavailable).
- Home Assistant 2025.x or newer and the integration at **0.6.31+** for the
  top-level `category`/`title`/`msg_type` attributes. The event trigger and
  `raw`/`delay_s` have worked since 0.6.30.
- The XPENG phone app, to fire an X-Combo when you want a test notification.

## 1. Find your entity and the event

Every entity id contains the last six characters of your VIN. Replace
`<vehicle>` with those six characters throughout; Settings → Devices & Services →
XPENG, or Developer Tools → States, shows the real ids.

The two surfaces this tutorial uses:

| Surface | What it is |
| --- | --- |
| `xpeng_notification` | A bus event, fired once per new Message Centre item (and per rare `msg_type=3` push). Carries the whole flattened record in `trigger.event.data`. |
| `sensor.xpeng_<vehicle>_last_notification` | A diagnostic sensor whose **state is the latest message text** and whose attributes carry the same fields. |

Watch it happen before writing anything: **Developer Tools → Events → Listen to
events**, type `xpeng_notification`, start listening, then fire a combo from the
XPENG app. The notification appears on the integration's next poll — up to the
**Message Centre poll interval** (default **300 s**, settable under Configure).

If the event never arrives, jump to [Troubleshooting](#troubleshooting).

## 2. Create the capture automation

Settings → Automations → **Create automation** → three-dot menu → **Edit in
YAML**, and paste this (or put the same YAML in a package):

```yaml
- alias: XPENG: capture notifications
  description: >-
    Records every xpeng_notification event, text included. The event fires once
    per Message Centre item; the sensor's state only changes when the text does.
  triggers:
    - trigger: event
      event_type: xpeng_notification
  conditions: []
  actions:
    - action: logbook.log
      data:
        name: "XPENG {{ trigger.event.data.category | default('notification') }}"
        message: >-
          {{ trigger.event.data.message | default('(no message text)') }}
          | msg_id={{ trigger.event.data.msg_id | default('?') }}
          msg_type={{ trigger.event.data.msg_type | default('?') }}
          claimed_at={{ trigger.event.data.timestamp | default('?') }}
```

What the pieces do:

- The **event trigger** is the capture form: one firing per new item, even when
  two messages share the same text.
- `logbook.log` keeps the line in the Logbook/history database, where it persists
  for the recorder's retention (10 days by default) and is visible on the Logbook
  dashboard — no extra card or notification needed.
- `name` is what the Logbook list shows; `message` is the line you can check
  against the text you configured.

Prefer a phone notification instead of (or as well as) the Logbook line? Add a
`notify.mobile_app_your_phone` action with the same `trigger.event.data.message`.

## 3. Fire a combo and verify

1. In the XPENG app, fire an X-Combo that sends a phone notification with text you
   will recognise.
2. Within one poll interval, the Logbook shows a line like:

   ```
   XPENG XPMOBILE-VEH  sensor.xpeng_123456_last_notification  2026-10-27 21:34:15
   Send HA message Benachrichtigung This is a longer message | msg_id=XPMOBILE-VEH:1564… msg_type=LINK claimed_at=2026-10-27T10:34:15+00:00
   ```

3. Check the sensor as well: its state is the message text, `count` has
   incremented, and `recent` holds the last five records with their `raw`.

If the text is in the Logbook line, capture works end to end. If only
`msg_id`/timestamps appear, the message text was not in the record — see
[the raw record](../guide/notifications#the-raw-record) and
[the field-rename checklist](#when-a-field-rename-breaks-the-text).

## 4. Read the record

`trigger.event.data` (and the sensor's attributes) carries the flattened record:

| Field | Example | Meaning |
| --- | --- | --- |
| `message` | `Send HA message …` | The text, with the app's HTML stripped. The field to automate on. |
| `title` | `XCOMBO-Benachrichtigung` | The notification's title. |
| `category` | `XPMOBILE-VEH` | Which Message Centre list it came from; `None` for an MQTT push. |
| `msg_type` | `LINK` | The app's content type. `LINK` is what X-Combo notifications use. |
| `msg_id` | `XPMOBILE-VEH:1564…` | Stable id, namespaced by category. Use it to de-duplicate downstream. |
| `timestamp` | `2026-10-27T10:33:46+00:00` | When XPENG says the message was created (Message Centre `createTime`). |
| `collected_at` | `2026-10-27T10:34:15.32+00:00` | When the poll recorded it. |
| `delay_s` | `29.0` | `collected_at` − `timestamp`: the poll latency, stamped once. |
| `source` | `rest` | `rest` for a polled Message Centre item; absent for an MQTT push. |
| `raw` | `{…}` | The record before parsing, including `messageContent` as the original JSON *string*. |

The six Message Centre categories (`XPMOBILE-VEH`, `-PUS`, `-CHA`, `-SER`,
`-ORD`, `-JOY`) are listed in [Notifications](../guide/notifications#the-six-categories).
The event fires for all of them, so add a condition when the automation is about
one kind of message:

```yaml
conditions:
  - condition: template
    value_template: "{{ trigger.event.data.category == 'XPMOBILE-VEH' }}"
```

## When a field rename breaks the text

The integration parses the text out of `messageContent`, an HTML/JSON blob that
XPENG can change. If a release starts showing an empty `message`:

1. Read `raw` from the event (`{{ trigger.event.data.raw | tojson }}` in a
   template, or the sensor's `raw` attribute). It contains exactly what arrived,
   with the original field names.
2. Report it (or fix the parser) from that record — no need to reproduce the
   notification to see its shape. `raw` is deliberately not parsed, so it keeps
   fields the current parser does not know about.
3. If you need the raw record in the Logbook, log
   `{{ trigger.event.data.raw | tojson }}` instead of `message`.

Turn on debug logging while investigating:

```yaml
logger:
  logs:
    custom_components.xpeng: debug
```

The parser dumps every Message Centre item at DEBUG (`Message-centre item raw:`),
before parsing it.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| No event on first poll after a restart | Expected: the first poll primes a baseline and fires nothing, so a restart does not replay the inbox. A *new* notification will fire. |
| A message that arrived while Home Assistant was down never fired | It was absorbed into the baseline. It is still in `recent` and `count` after startup, but no event fired for it. |
| Nothing fires at all | Integration loaded? `binary_sensor.xpeng_<vehicle>_credentials_valid` **on**? The event is also fired for rare MQTT pushes, but Message Centre items only arrive through the poll. |
| Text is missing, id and timestamps are there | This is the field-rename case above: read `raw`. |
| Two identical messages produce one Logbook line | You are triggering on the sensor state (the text), not the event. Use the event trigger from this tutorial. |
| `delay_s` looks like the poll interval | That is correct — a poll cannot beat its own interval. Lower **Message Centre poll interval** under Configure; each poll is six API requests, and the floor is 60 s. |
| X-Combo does not fire from a `xpeng.execute_scene` call | Expected: the service is in the **Advanced and raw commands** group (disabled on new installs), and a local scene cannot be one-key started from the cloud. Fire the combo in the app; use this automation to capture the result. See [Command permissions](../reference/command-permissions). |
| Nothing at all, log shows TLS/WAF errors | The Message Centre host uses a public certificate; see [a different certificate authority](../guide/notifications#a-different-certificate-authority). |

## Where to go next

- [Notifications](../guide/notifications) — poll interval, categories, the raw
  record and where notifications come from.
- [Entities](../reference/entities) — every entity the integration creates.
- [The vehicle card tutorial](vehicle-card) — if you want the car on a dashboard
  as well.

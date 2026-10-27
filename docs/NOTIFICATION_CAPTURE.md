# Where an X-Combo notification's text lives, and what a Message Centre record can be tied to

Research note, 2026-10-27. Read this before changing the notification path or
before claiming that a combination of X-Combo plus Message Centre can capture a
scene's configured text by field. It cannot: the record has no scene field. The
only durable capture source is the Message Centre record itself, which is why
the integration now exposes that record verbatim as `raw` on
`sensor.<vehicle>_last_notification` and in the `xpeng_notification` event.

Measured against one EU car (F30/G9, `vehicleTypeCode` `FA`, sale region AU,
XOS 5.9.5.8909), integration 0.6.29, Home Assistant 2026.10.4, using the
integration's own signed REST client and the config entry's stored tokens from
the HA host. Calls are read-only apart from one attempted local-scene
one-key start, called out below.

## The Message Centre record

`POST https://msgcenter-oversea-eur.xiaopeng.com/v3/app/notification/page`

```json
{"param": {"firstClassificationCode": "XPMOBILE-VEH"}, "size": 30,
 "uid": "<account uid>", "page": 1}
```

Every item in the `XPMOBILE-VEH` list (90 items checked across three pages,
including X-Combo notifications, door/lock events and power-off events) has
exactly these five top-level keys:

```json
{
  "id": "1564701551662501888",
  "messageId": "1564701551662501888",
  "read": false,
  "createTime": "2026-10-27 10:05:20.0000",
  "messageContent": "{\"msgContent\":{\"description\":\"<p>...</p>\",\"title\":\"XCOMBO-...\"},\"msgType\":\"LINK\",\"title\":\"XCOMBO-...\",\"category\":\"XPMOBILE-VEH\",\"content\":\"<p>...</p>\",\"desc\":\"<p>...</p>\"}"
}
```

`messageContent` is a JSON **string**, and the human text appears in
`msgContent.description`, `content` and `desc` (all HTML). That is the text the
app shows and the text the integration parses. There is no `sceneId`, `actionId`,
`bizId` or sender field anywhere on the record - the five keys above are all of
it, for every one of the 90 items.

## The detail endpoint: there isn't one to call

`msgType` values seen: `LINK` (all of the above). The app's "View Details" for a
`LINK` message shows the same title/body already present in the list item; no
richer body is fetched. Sixteen candidate paths on the msgcenter host were
tried - `/v3/app/notification/{detail,info,get,query,content,body,msgDetail}`,
`/v3/app/message/{detail,info}`, `/biz/v5/message/{detail,info,get}`, the same as
GET with `id`/`messageId`, and a REST-style `/v3/app/notification/<id>` - and
every one answered HTTP 404 with the WAF's generic body:

```json
{"code":400,"data":null,"msg":"Server unavailable. Please try again later"}
```

`/biz/v5/message/category` and `/biz/v5/message/listByCategory` answer the same
404 on this host even though the app contains their paths, so the WAF gives the
same body for "no such route" and "wrong request"; this is a negative result, not
a permissions problem to retry around. The page item is the whole message.

## The combo definition: text is there, attribution is not

`POST /personal-tailor/v3/scene/mine` returns scene **summaries** only:

```json
{"sceneId": "...", "name": "...", "status": "RUNNABLE", "source": 1,
 "desc": "...", "sceneType": "local", "sceneIcon": "...",
 "sceneIconId": 0, "preSceneId": "...", "model": "REPEAT"}
```

No actions, no notification text. The notification action's configured text is
reachable only from the scene-detail endpoint, whose body shape is not the one
the old `get_xcombo_share_info()` assumed:

`POST /personal-tailor/v3/scene/detail`

```json
{"sceneId": "<scene id>", "vin": "<vin>", "source": 0,
 "carType": "<vehicleTypeCode>", "vehicleType": ""}
```

`source` (0 or 1 both accepted) and `carType` are required; a missing
`vehicleType` fails validation even though an empty string is accepted. The
response's `data.rule.action` is the action tree, and a "Send phone
notification" action looks like:

```json
{"leafId": "<menu item id>", "actionType": "atom",
 "execution": {"id": "<action resource id>",
               "tecPoint": "remote.send.message", "resourceType": "ATOM_CMD"},
 "arguments": {"uid": "<account uid>", "name": "<account name>",
               "text": "<the text the combo sends>"}}
```

So the configured text is available per combo - but nothing in a fired message's
record points back at the combo that produced it. Matching message text to
`arguments.text` is the only link, and two combos may legitimately send the same
text. **A combo-definition-based capture is therefore unusable for attribution**,
which is why the integration captures the Message Centre record and keeps it
raw instead.

## One-key start

`POST /personal-tailor/v3/scene/lifecycle` with `{"sceneId", "vin"}` (the call
behind the `xpeng.execute_scene` service) returned HTTP 200 carrying
`{"code":18070030,"msg":"Interne Dienstausnahme"}` for a local (`ruleType:
LOCAL`) notification-only scene, and no Message Centre item attributable to that
call appeared. Local scenes execute on the car; the REST one-key start is not a
dependable way to make one fire remotely. Do not use it as a capture trigger or
as an integration test - fire the combo from the app instead.

## What the integration does with this

- `parse_notification_item()` keeps the unparsed item as `raw` (with
  `messageContent` still a JSON string) and logs it at DEBUG before parsing.
- The last-notification sensor exposes `raw` for the latest record, and
  `recent` carries each record's raw; the `xpeng_notification` event payload
  carries it for both sources - the Message Centre item for the REST poll, and
  the MQTT envelope (`msg_type`, `service_type`, `msg_id`, `msg_content`) for a
  `msg_type=3` push, which `_fire_notification()` snapshots before flattening.
- When XPENG renames or moves a field the parser reads, the fix can be made from
  a captured event or the entity attributes: the original field is still in
  `raw`, in the same shape it arrived.

## Reproducing this

On the HA host (the config entry holds the tokens and `/config/custom_components/xpeng/certs`
holds the mTLS pair), load `xpeng_api` by path and call
`get_notifications(None, tenant, tokens, classification="XPMOBILE-VEH")`; the
module resolves its own certificate directory. `parse_notification_item()` on
any item returns the flattened record and its `raw` copy.

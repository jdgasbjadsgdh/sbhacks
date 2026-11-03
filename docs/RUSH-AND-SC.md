# Rush and optional preview — Mac / Web v2, 2 November 2026

Rush is the only offered hold on Mac/Web v2. Arm it immediately before the
next room's loading screen; in SC, arm before the last generator is destroyed.
The loading gate applies to ordinary rooms, side/safe rooms, normal/elite
missions and automatic SC boss entry. It does not skip intermediate rooms.

**Preview: connect within 10 seconds or you'll be sent to Eschaton.**
Preview releases the current asset readiness once and holds the server-created
world's readiness. It shows current room/floor and allows free camera. The
countdown includes map arrival and natural recovery; it does not restart after
a reconnect or automatically finish the hold. Connect/F10 from an early hold
instead finishes normal loading directly, without requesting a preview.

## Loading and recovery

Rush holds PVID_LOADED (22) before CreateWorld where supplied. This phase has no
current room/platform data and works without a live WorldClient. Same-server
room transitions can skip it. Rush then tries one deferred native/socket
reconnect to obtain it; if absent again, it reports a world-ready fallback.
The fallback has the short preview warning. No periodic refresh remains.
Natural disconnects preserve active hold intent. Finish/Cancel takes precedence
over a queued retry; stale worlds/sockets and already spawned players cancel it.

A client update cannot extend the server deadline or promise a retained mission.
Older long early-hold trials are historical, not evidence of current SC lifetime.
Live early Rush/SC retention after the latest game update remains unverified.

## Disconnect + hold

Mac/Web v2 place the button beside Rush. It requires a living spawned character
and no active hold, then queues one close while Rush remains armed for recovery.
Before closing, the deferred action rechecks the socket, room and character.
Repeated activation, dead/replaced characters, stale sockets and canceled or
expired requests cannot produce a second close. There is no health trigger.
Mac retains its configurable native shortcut; Web uses the current tab's button.
Group arming remains separate from emergency activation.

## Data available before preview

| Stage | Available data |
| --- | --- |
| LoadPVid / early asset hold | Asset version; no live map/platform positions |
| CreateWorld and world updates | Current world properties, objects and motion |
| Another spawned account | That client's live map; no observer transfer feature is included |

Hiding rendering or pausing local input cannot undo a server-created world.
The plugin never labels cached/origin room data as current destination data.
No platform settlement detector, guaranteed protection or chest timer is included.

## Install and limits

Use the complete platform ZIP in the repository README. Mac installs with
INSTALL.command; Web installs with INSTALL.html into its Overrides folder.
Both preserve existing unrelated settings, back up replaced files and leave
activation to a later normal launch/reload. No client is launched during checks.

Native regressions exercise room/SC early gates, exact-once continuation,
queued closes, recovery, input/time/acks, camera, compact UI and hidden controls.
Web uses the actual upstream ABI/manager and isolated Chromium for transport,
DOM, multi-tab arming, manual disconnect, downloads and narrow layouts.
These tests validate client behavior; live server retention remains unverified.
Windows retains its previously published v1 build and older controls in this update.

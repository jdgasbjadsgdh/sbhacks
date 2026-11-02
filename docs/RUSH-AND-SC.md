# Rush hold and the SC timeout — 2 November 2026

**Warning: Boss hold and Preview room kick you after about 10 seconds.**
Preview uses the same world-ready hold as Boss hold. Neither is a long wait.
The warning appears in the Mac, Windows and web loading panels, even before
you arm a hold. A client update cannot remove a server deadline.

## Rush before any boss

Choose **Rush hold immediately before the desired boss transition**. It works
with the next entry, regardless of boss family or normal/elite difficulty;
it does not skip intermediate rooms. In SC, arm before the last generator
is destroyed. Boss hold still skips intermediate rooms, but uses the short
world-ready hold described above.

Rush first holds the early asset-loading acknowledgment. Some in-mission
transitions omit that step and send a world directly. The new version queues
**one reconnect**, after the current network callback has returned, to try to
reach the early asset phase on a fresh connection. Spawn readiness remains
held throughout. This is an experimental fallback, not a verified server fix.

If that fresh connection also omits the early phase, the panel remains in a
world-ready fallback. It does not deliberately reconnect repeatedly. Natural
server disconnects can still occur. Finish/Cancel take precedence over a
queued Rush retry; a changed world, socket or spawned character cancels it.
The server can select another room or expire the mission during recovery.

**EARLY HOLD means no current map or platform data is available.** Wait there,
then choose Preview room only when ready for a short inspection. Preview ends
the early wait. Use Reconnect promptly to request a fresh normal spawn.
Finish loading/F10 during an early Rush hold instead continues normal loading
directly. Timed mode still advances into preview automatically, so its preview
also has the short deadline.

## Can SC platforms be watched without entering the short preview?

The inspected client protocol separates these stages:

| Stage | Available information | What it can show |
| --- | --- | --- |
| LoadPVid / early asset hold | Asset version string | No live platform positions or current room |
| CreateWorld and subsequent world updates | World properties, objects and motion changes | Current map and platform movement; starts the short hold |
| Another normally spawned client in the same mission | That client's current world updates | A live view while the held client waits early |

The native `LoadPVid` structure contains a `pvid` string, not world objects.
`CreateWorld` contains `worldprops`, `worldstate`, `spawnobj` and `worldid`.
Suppressing local rendering, discarding objects, or pausing receive processing
does not undo a world the server has already created or restart its deadline.

No supported single-client method was found to receive accurate live platform
positions while staying in the asset-only phase. A cached platform position
would become stale, and extrapolating one motion descriptor cannot predict
later server-issued splits, phase changes or settlement. This release does
not label such guesses as current positions and adds no automatic settlement
detector.

The available workaround is to watch on another spawned account while the
held account waits early, or open a brief preview near the intended reconnect
time. Receiving telemetry from another account would require an additional
observer feature; it is not included in these packages.

## Evidence and validation limits

Local 2 November logs include `jungle_boss` and `caveHard` world holds ending
in socket hangup at 9.962 and 9.952 seconds. Earlier world-hold trials ended
near 25 seconds. Separate early asset holds finished manually after 60.078,
76.261 and 103.499 seconds. These establish observed behavior on those trials,
not a guaranteed SC retention duration or a server rejection explanation.
The SC timeout warning also incorporates the player's report.

Offline tests exercise the actual deferred native I/O queue, all three state
machines, simulated boss entries, fresh asset holds, unchanged ordinary
traffic, failed/duplicate callbacks, fallback without a retry loop, stale
connections, Cancel/Finish, installers and browser UI. No live game is started
or restarted during validation. Live SC confirmation of the new reconnect
attempt remains pending, including a Windows in-game trial.

## Updating

Use the complete ZIP linked from the repository README. Mac uses
INSTALL.command or UPDATE_EXISTING.command; Windows uses INSTALL.cmd with its
existing SBPE 1.7.0 folder; web uses INSTALL.html with its Overrides folder.
Existing configuration and explicit key bindings are retained. Restart native
clients or reload the web page when ready to load the new code. Installers do
not start or restart games. Earlier downloadable archives remain available.

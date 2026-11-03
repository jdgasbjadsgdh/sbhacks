SBPE Connection — Web v2 — 2026.11.02-connectivity.2

Requires desktop Chrome/Edge and WebBreak build 1574197275. Extract the entire
ZIP. In the game tab, DevTools > Sources > Overrides must point at a local
folder with permission; keep DevTools open for Overrides. Open INSTALL.html,
choose that same folder and click Install / update. The installer preserves
WebBreak settings and saves a backup. Reload your game when ready; installation
does not reload it. The complete ZIP includes the generated client and payload.

F8: panel / restore hidden UI. F9: Rush / cancel unused arm. F10: Connect.
Rush hold: next room loading, including SC. Arm before SC's last generator.
Disconnect + hold: one validated deferred close of this tab's current socket;
Rush remains armed on recovery. Requires a living character, no active hold
and at least ten seconds between uses. It does not broadcast to other tabs.
Preview room: view the server-selected map while keeping spawn held.
WARNING: connect within 10 seconds or you'll be sent to Eschaton.
Connect: finish early loading, or reconnect from a loaded preview. F10 with
an unused Rush arm cancels that arm without a disconnect.
Free camera: WASD/arrows, Shift fast. Cancel hold: disarm/finish.
X collapses the panel; Hide all UI hides panel and tab; F8 restores them.
Save log downloads local metadata. Reloading discards unsaved web logs.
Arm all connected web tabs broadcasts Rush only within this origin/profile.

The compact 328px panel has Rush, Disconnect + hold, Preview, Connect, Free
camera and Cancel. Boss, Timed, refresh and Back to Rush are absent. The preview
countdown includes map arrival/recovery and never auto-connects or refreshes.
A room that skips early loading triggers at most one fresh-connection attempt,
then a short world-ready fallback if still absent. Server timeouts and mission
retention remain uncontrolled. No movement/Sync or automatic platform detector
is included. Offline ABI/transport, installer, multi-tab and real Chromium UI
checks pass; live SC retention is unverified. See RUSH AND SC.md.

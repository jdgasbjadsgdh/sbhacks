SBPE Connectivity / Loading Controls for WebBreak
25 October 2026 | Version 2026.10.25-connectivity.1

INSTALL / UPDATE
1. Extract the ENTIRE ZIP, keeping its files and folders together.
2. Open INSTALL.html in desktop Chrome or Edge.
3. Choose the same Overrides folder selected in the StarBreak tab's DevTools.
   Select the folder containing www.starbreak.com, or that domain folder itself.
4. Click Install / update. Existing WebBreak settings are preserved and the
   previous override is backed up before it is replaced.
5. Save any test log you want to keep, then reload your game page when ready.
   Keep DevTools open so its local override applies.

The installer does not reload your game. Copying files does not update a page
that is already running. The included www.starbreak.com folder is the manual
fallback; the installer is preferred for preserving custom WebBreak settings.
First-time Overrides instructions are included in INSTALL.html.

HIDE EVERY LOADING CONTROL
Click Hide all UI in the top right of Loading controls. Both the full panel
and its collapsed tab disappear. F8 restores the panel; on a Mac keyboard
you may need Fn+F8. Keep the game page focused and close chat first.

Hiding is local to this browser tab. It does not cancel a hold, reconnect,
change camera selection or stop the timer. F9/F10 and free-camera movement
keep working while hidden. A natural reconnect or arm-all message does not
reopen the UI. A new page load starts with the panel visible again.

Close panel is still available: it collapses just the panel, leaving a small
clickable tab. F8 normally toggles that panel; after Hide all UI, F8 first
restores it instead. Repeated/modified function keys and typing do not restore
the UI accidentally.

QUICK USE
Rush hold: arm before the next portal or automatic boss transition. It waits
at the earlier loading stage where available.
Boss hold: let intermediate rooms load; hold spawn in the next boss room.
Preview room: advance an early wait into a visible map with spawn still held.
Free camera: in a map preview, use WASD/arrows; Shift moves faster.
Reconnect: finish a map hold through fresh normal recovery. During an early
wait this button can say Finish loading or Next: preview; read its label.
Timed: 360s: early wait, then automatic preview after six minutes; spawn still
requires manual finish. Six minutes is a test interval, not an SC guarantee.
Cancel hold: disarm or finish the active hold; it can make you spawn.
Save log: download the current session before refreshing or closing.

SC: arm Rush hold before the last generator is destroyed, wait through the
boss load, choose Preview room to inspect the platforms, then Reconnect when
ready. The server chooses the room/checkpoint and can return you to Eschaton.
There is no automatic final-platform or chest detector.

KEYS
F8: panel / restore hidden UI. F9: arm selected mode / cancel an unused arm.
F10: next / finish / reconnect. Select Rush/Boss/Timed with its button first
so you know which mode F9 will arm. These web loading shortcuts remain fixed.

Arm all connected web tabs applies the next Rush/Boss/Timed arm to same-origin
tabs in the same browser profile/storage partition. Active holds are preserved.
UI hiding is local and is not broadcast. Separate/private profiles and native
Mac/Windows clients are separate groups. This web package contains loading
controls, not the native Emergency hold or shared-movement/Sync panel.

DIAGNOSTICS / COMPATIBILITY
This package targets WebBreak build 1574197275. Existing user settings and the
original game body are preserved by the installer. No name-entry/spawn timing
observer is included. Loading metadata is local until you save it; no feature
logs are uploaded. Unsaved web logs disappear on page reload.

The update has isolated Chromium DOM/ABI and multi-tab tests, plus loading,
transport and installer regressions. The UI changes do not establish a fix
for independent connection loss or guarantee mission retention.
See TUTORIAL.txt for complete installation, loading-state and platform details.

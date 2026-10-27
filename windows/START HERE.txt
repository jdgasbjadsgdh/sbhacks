SBPE Emergency Hold for Windows / Sandboxie
24 October 2026 | Version 2026.10.24-emergency.3

INSTALL
1. Close the Windows StarBreak client when ready to update.
2. Extract the ENTIRE ZIP. Keep all files and subfolders together.
3. Double-click INSTALL.cmd and choose the existing SBPE Windows 1.7.0 folder
   containing pypy, plugins, config.ini and run.bat. You can also drag that
   SBPE folder onto INSTALL.cmd.
4. Wait for Loading plugin installed, then start that folder's run.bat.

This is a plugin update, not a complete copy of Windows SBPE or the game.
It uses SBPE's bundled 32-bit PyPy; no separate Python or administrator
access is required. The installer backs up replaced files and preserves
existing custom tools, settings and assigned controls. It does not launch
or restart games. Copying only loading_probe.py is insufficient.

CHANGE KEYBINDS IN-GAME
Click Keys at the top of Loading controls v6. The editor lists Emergency hold,
loading-panel toggle, arm-selected, Rush hold, Boss hold, room preview, Resume /
reconnect, free camera, timed hold and cancel hold. Click a key slot and press
your key. Esc cancels an assignment (or closes the editor); Backspace clears
a slot. Prev/Next handle smaller windows. Changes save and apply immediately.

Existing shortcuts remain until changed. New direct-action shortcuts start
unbound. Conflicting plugin/tool shortcuts are rejected; clear an existing
slot first if you want to reuse its key. The plugin does not execute the key
that you just used to assign a binding. Set hotkey on the Emergency hold panel
opens its row in this same editor. Other clients sharing the same config file
will see the saved settings when their normal config reload occurs.

EMERGENCY HOLD
While your living character is spawned, press F4 or click Disconnect + hold
in the left Emergency hold panel. This requests one normal reconnect while
keeping Rush armed, so the next character spawn is held. Resume / reconnect
finishes the hold. The normal finish shortcut, usually F9 on Windows, also
finishes it. The server chooses the room and spawn point on recovery.

F4 is assigned only when free. Your existing F4 custom-tool binding is never
replaced. The panel displays the assigned shortcut or GUI only. Click Set
hotkey, then press an unused key to change it. Esc cancels; Backspace clears.
Loading-panel shortcuts and existing SBPE tool bindings are rejected as
conflicts. A copy of the previous config is saved in loading-probe-backups/.

The shortcut is limited to the focused client, blocked during text input and
control dialogs, and triggers once per key press. There is no automatic
low-health activation. Wait ten seconds between activations. The key works
with the Emergency hold panel closed; click its collapsed tab to reopen.
Small windows start with that panel collapsed.

Emergency hold affects ONE client. Arm all clients does not broadcast it.
Natural reconnects during the hold keep readiness blocked. After a recovery,
free camera remains selected and resumes when a valid held map returns.

LOADING / MULTIBOX CONTROLS
Existing bindings are preserved. Fresh installs try F6 for the loading panel,
F7 to arm the selected hold, F9 to finish. F11 is a panel fallback. The actual
keys are shown at the bottom of Loading controls v6 and in loading-status.txt.
Rush hold initially selects the early wait. Preview room loads a map while
keeping character spawn held; Reconnect finishes through a fresh connection.

For Sandboxie, install into the shared SBPE folder outside the sandbox, then
run its run.bat in each box. Each copy needs the same multibox_group_key and
multibox_port. Restrictive network policies must allow IPv4 loopback UDP
coordinator port 47812 and private reply ports for the game. No Sandboxie
network or IPC policies are changed by the installer.

The Multibox panel sits below Loading controls, with per-client health and
Reconnect buttons, Reconnect all, Controls ON/OFF and Sync. Controls starts
OFF. Shared movement uses each client's own game bindings in the same room.
Sync turns controls ON and walks the other characters toward the client
where you clicked Sync. Keep that window focused. Controls OFF stops it.
Update every client to this version, including private Sandboxie copies.
The status beneath the buttons explains room mismatch, missing native input,
chat/settings pauses and missing focus. More detail is in loading-status.txt
beside run.bat; this file contains no group key or account credentials.
The Arm all clients checkbox applies Rush/Boss/Timed arming to the connected
group while preserving active holds. See CONNECTIVITY GUIDE.txt for details.

WHAT THIS BUILD CONTAINS
Emergency hold, GUI hotkey picker and local timing/health metadata; the v4
free-camera recovery fix; compiled-runtime mouse routing and stable text
textures; readable GUI sizes; Windows Sandboxie multibox and arm-all support.
No private Mac settings, account data, game files or recordings are bundled.

VALIDATION / LIMITS
Windows native callback composition, actual x86 ABI adapters, state recovery,
hotkeys, config persistence, installer upgrades and GUI fixtures passed
offline. A real Windows/Sandboxie in-game trial is still required.

On Mac, an observer saw the character disappear and it returned to the same
mission with unchanged HP in a trial. That does not establish protection
against incoming damage. The feature cannot undo server-accepted damage or
death, guarantee instant disappearance, reserve a checkpoint or keep a mission
alive. Server disconnects and a return to Eschaton remain possible.

SUPPORT / DISABLE
Loading controls v6 identifies the updated UI. If clicks fail, share
loading-status.txt and the relevant warning from remote.log. UNAVAILABLE
means native methods did not pass initialization; build/byte checks remain on.

In [plugin_loading_probe] in config.ini:
emergency_enabled = no  disables Emergency hold only.
emergency_key =         leaves the button available without a shortcut.
enabled = no           disables the whole loading plugin.

Metadata logs are local in loading-tests/. They do not record passwords,
Steam tickets, cipher material or packet contents; no external upload occurs.
Keep loading-probe-backups/ if you want to restore the previous files.

SBPE by atomizer. Game/resources by Crunchy Games. Bundled pyelftools 0.29
uses the included public-domain license. This package is for Windows SBPE
1.7.0; it does not add Emergency hold to WebBreak.

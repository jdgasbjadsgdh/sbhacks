# SBPE Disconnect & Loading Controls

Loading holds, room preview, free camera, and manual disconnect/reconnect controls
for StarBreak. Mac and Windows include **Emergency hold**: disconnect a spawned
character and hold its next spawn until you choose to continue.

## Downloads

Download the ZIP for your platform and **extract the entire archive** before
running its installer. Use these complete packages rather than copying one
plugin file or running an installer from GitHub's source preview.

| Platform | Download | Package version |
| --- | --- | --- |
| Mac SBPE | [Download Mac ZIP](https://github.com/jdgasbjadsgdh/sbhacks/raw/refs/heads/main/downloads/SBPE-Emergency-Hold-Mac-2026-10-24-v3.zip) | `2026.10.24-emergency.3` |
| Windows SBPE / Sandboxie | [Download Windows ZIP](https://github.com/jdgasbjadsgdh/sbhacks/raw/refs/heads/main/downloads/SBPE-Emergency-Hold-Windows-2026-10-24-v3.zip) | `2026.10.24-emergency.3` |
| WebBreak | [Download Web ZIP](https://github.com/jdgasbjadsgdh/sbhacks/raw/refs/heads/main/downloads/SBPE-Connectivity-Web-2026-10-25.zip) | `2026.10.25-connectivity.1` |

These are the clean share-package snapshots published on 24–25 October 2026.
Their original archives, source files, version information and SHA-256 checksums
are included here. Personal account settings and test recordings are excluded.
Later changes in a private/local install are not implied by these version numbers.

## What each version supports

| Feature | Mac | Windows / Sandboxie | WebBreak |
| --- | --- | --- | --- |
| Rush, Boss and Timed loading holds | Yes | Yes | Yes |
| Room preview and free camera | Yes | Yes | Yes |
| Manual Emergency hold while spawned | Yes | Yes | No |
| Native multibox health, shared movement and Sync | Yes | Yes | No |
| Arm holds on connected accounts/tabs | Native Mac group | Native Windows group | Same-browser-profile web tabs |
| Hide every connectivity panel/tab | Yes | Collapse panels individually | Yes |
| Change shortcuts in-game | Controls → SBPE | **Keys** in Loading controls | Fixed loading shortcuts in this export |

Mac, Windows and browser groups are separate. In these exported versions,
**Emergency hold affects only the client where it is activated**; the
**Arm all clients** checkbox broadcasts loading-mode arming, not Emergency hold.

## Install on Mac

Requires the supported Intel StarBreak Steam client. Apple silicon uses Rosetta.
The original game executable is not bundled.

1. Download and extract the Mac ZIP.
2. Close the StarBreak client you want to update when you are ready.
3. For an existing Mac SBPE installation, run **INSTALL.command** and follow the
   prompts to choose that SBPE folder. It backs up replaced files and preserves
   existing key choices and unrelated settings.
4. Launch through your normal SBPE launcher. For a separate extracted installation,
   use **RUN.command**; see its `START HERE.txt` for first-launch requirements.
5. Change Emergency hold under **StarBreak Controls → SBPE → Emergency hold**.

The installer does not restart the game. Native code changes require a later
launch through SBPE. The prebuilt `sbpe-mac.dylib` is inside the download; rebuilding
is optional. The matching native source is in [mac/src](mac/src).

Full Mac instructions: [START HERE](mac/START%20HERE.txt) ·
[Complete tutorial](mac/TUTORIAL.txt).

## Install on Windows

Requires **Windows SBPE 1.7.0 and its bundled 32-bit PyPy**. This is an update for
an existing SBPE installation, not a complete Windows game/SBPE distribution.

1. Download and extract the Windows ZIP.
2. Close StarBreak before updating its SBPE folder.
3. Double-click **INSTALL.cmd**, then choose the folder directly containing
   `pypy`, `plugins`, `config.ini` and `run.bat`.
   Alternatively, drag that whole SBPE folder onto `INSTALL.cmd`.
4. Wait for **Loading plugin installed** and launch the usual `run.bat`.
5. Click **Keys** at the top of Loading controls to edit shortcuts.

Keep all extracted files and subfolders together. Copying only
`plugins/loading_probe.py` leaves out required native bridges and helper modules.
The installer backs up replaced files and preserves unrelated settings and
existing explicit shortcuts. No separate Python installation is required.

For Sandboxie, update the shared SBPE folder outside the sandbox, then launch
`run.bat` inside each box. Private SBPE copies need the update individually.

Full Windows instructions: [START HERE](windows/START%20HERE.txt) ·
[Complete tutorial](windows/TUTORIAL.txt).

## Install on WebBreak

Requires desktop Chrome or Edge and WebBreak build **1574197275**.

1. Download and extract the **entire Web ZIP**. It includes the generated game
   override and installer payload omitted from the source-only `web/` folder.
2. In the StarBreak tab, open DevTools → Sources → Overrides, select a local
   Overrides folder, and grant access. Keep DevTools open when using overrides.
3. Open the extracted **INSTALL.html** in Chrome or Edge.
4. Select the **same Overrides folder**, click **Install / update**, then reload
   the StarBreak tab when ready. The installer preserves WebBreak settings and
   backs up the previous override.

The web installer does not refresh your game. This export has loading holds and
preview, but **does not include the native Emergency hold or movement/Sync panel**.

Full web instructions: [START HERE](web/START%20HERE.txt) ·
[Complete tutorial](web/TUTORIAL.txt).

## Default shortcuts

Existing assigned shortcuts are preserved, so the keys displayed by your panel
are authoritative. On a Mac keyboard, function keys may require **Fn**.

| Action | Mac defaults | Windows fresh-install defaults | Web |
| --- | --- | --- | --- |
| Emergency hold | F4 | F4, only if free | Unavailable |
| Open/close Loading controls | F8 | F6; F11 fallback | F8 |
| Arm selected hold / cancel unused arm | F9 | F7 | F9 |
| Continue / finish / reconnect | F10 | F9 | F10 |

On Mac, select a key slot under **Controls → SBPE** and press the new key;
Backspace clears a slot. Three alternative Emergency hold bindings are supported.
F8/F9/F10 remain reserved for loading controls in this export.

On Windows, click **Keys**, select an action's key slot, then press a new key.
Esc cancels assignment; Backspace clears it. The editor saves immediately and
rejects conflicting shortcuts. Newly available direct-action shortcuts start
unbound. **Set hotkey** on Emergency hold opens its row in the same editor.

## Quick tutorial

### Wait before entering a room

1. Before a portal or automatic boss transition, click **Rush hold**.
2. Enter the transition. The panel should report an early hold where that loading
   stage is available.
3. Wait as long as you choose, subject to server connection/session limits.
4. Click **Preview room** to load the current map while keeping spawn held.
5. Optionally enable **Free camera**, then use WASD/arrows to look around;
   Shift moves faster.
6. Click **Reconnect** when ready to spawn through normal recovery.

### SC boss example

Arm **Rush hold before the final generator is destroyed**. Wait through the boss
load, then use **Preview room** to inspect the platforms. Reconnect when ready.
There is no automatic settled-platform/chest detector, and `Timed: 360s` is a
six-minute wait setting, not a guaranteed SC completion time.

### Emergency hold while already spawned — Mac / Windows

Press the assigned Emergency hold key, or click **Disconnect + hold**. It queues
one disconnect/recovery and holds the next spawn. Use **Resume / reconnect** or
the finish shortcut to return. Activation is manual, not based on low health.

Emergency hold is not an instant Home command. It cannot undo damage or death
already accepted by the server, guarantee immediate disappearance, or guarantee
that your mission/checkpoint remains available. Incoming-damage protection is
unverified.

## Button reference

| Button | What it does |
| --- | --- |
| **Rush hold** | Arms an early hold for the next map or boss load. |
| **Boss hold** | Allows intermediate rooms, then holds spawn in the next boss room. |
| **Preview room** | Advances an early hold into a visible map while spawn remains held. It does not reserve that room as your eventual spawn. |
| **Reconnect / Resume** | Finishes a map hold through fresh recovery. In earlier stages, read the button's current label: it may continue loading or advance to preview. |
| **Free camera** | Moves the camera during an unspawned map preview. Selection survives a natural reconnect while the hold remains active. |
| **Timed: 360s** | Waits six minutes, then advances to preview; spawning remains manual. |
| **Cancel hold** | Disarms or finishes the hold; finishing can make your character spawn. |
| **Close panel** | Collapses the panel to a tab. The hold continues. |
| **Hide all UI** | Mac/Web: hides the panels and tabs. F8 restores them; active holds continue. |
| **Arm all clients/tabs** | Applies the next Rush/Boss/Timed arm to connected compatible peers. Active holds are preserved. |
| **Controls ON/OFF** | Native multibox: enables/stops shared controls. |
| **Sync** | Native multibox: enables shared controls and moves followers toward the focused character. It is not a teleport or permanent guarantee of alignment. |
| **Reconnect all** | Native multibox: explicitly requests recovery for the connected group. |

## Multibox notes

Native clients must share the group key and coordinator port specified in their
platform guide. Windows uses IPv4 loopback UDP port **47812** plus private reply
ports. Sandboxie restrictions must permit that traffic; the installer does not
change Sandboxie policies. Never publish your personal group key.

Keep the client where you clicked Sync focused. Room mismatches, stale data and
chat/settings stop shared movement. **Controls OFF** releases mirrored input.
Web arming uses same-origin tabs in the same browser profile/storage partition;
private or separate browser profiles are separate groups.

## Troubleshooting and limitations

- **Hotkey does nothing:** focus the game, close chat/settings, check the actual
  assigned key in the panel, and use Fn if needed.
- **Windows buttons do nothing:** install the complete ZIP and relaunch via
  `run.bat`; the compiled mouse bridge is required. Check `loading-status.txt`.
- **Windows text is too small:** adjust the panel's A−/A+ controls or `ui_scale`
  under `[plugin_loading_probe]`; `0` uses automatic sizing.
- **Mac/Web UI disappeared:** F8 restores UI hidden by **Hide all UI**.
- **r stays at 0 or you return to Eschaton:** a hold does not fix underlying
  connection loss or prevent server timeouts/mission expiry. Preview is not a
  reservation of the eventual room or spawn point.
- **UNAVAILABLE:** native initialization/compatibility checks failed. Keep the
  checks enabled and share the relevant diagnostic message.
- **Save logs before reloading:** web logs are in memory until saved. Native
  loading metadata is local in `loading-tests/`; no automatic upload occurs.

For support, include the platform, package version, action and timing, and relevant
`remote.log` / `loading-status.txt` messages. Native logs may be replaced on launch,
so copy them before reopening after a failure. Remove private information before
sharing logs.

The exported Mac build has native regression and sanitizer checks. Windows has
30 offline tests, including real loopback peers and ABI/input/UI fixtures; a live
Windows/Sandboxie game trial is still required. Web has isolated Chromium
DOM/ABI/multi-tab tests. These checks do not establish guaranteed damage protection
or a cure for independent disconnects. Detailed validation is in
[downloads/manifest.json](downloads/manifest.json).

## Source and checksums

- [Mac source and launcher/install scripts](mac/)
- [Windows plugin, helper modules and installer](windows/)
- [Web plugin and installer source](web/)
- [How the loading states work](docs/HOW_IT_WORKS.md)
- [SHA-256 checksums](downloads/SHA256SUMS)
- [Credits](CREDITS.md) and [license](LICENSE)

Mac's prebuilt library and the generated WebBreak client/payload are inside the
complete platform ZIPs. Rebuild Mac with `BUILD.command` on macOS with Apple
Command Line Tools; rebuilding does not launch the game. This repository does
not include account credentials, personal multibox configuration, or recordings.

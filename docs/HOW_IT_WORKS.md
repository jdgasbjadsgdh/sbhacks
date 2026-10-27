# How the disconnect/loading plugin works

The plugin controls which parts of the normal client loading sequence are allowed
to finish. It does not create a different mission server or choose an arbitrary
checkpoint. Internal state names vary slightly between platforms.

## Loading sequence

1. **Idle:** ordinary play; no hold is armed.
2. **Armed:** a selected loading mode watches for its applicable transition.
3. **Early hold:** Rush mode waits before the map-loading stage completes, where
   that transition supports the early gate. The world may not be visible yet.
4. **Map hold / preview:** the client can display received world data, while the
   final spawn/readiness step remains held. Free camera can inspect available
   map data without moving a spawned character.
5. **Resume / reconnect:** the hold ends and normal recovery/loading continues.
   The server supplies the destination and spawn information.

**Boss hold** permits intermediate rooms and waits in an eligible boss room.
**Rush hold** targets the next applicable load, including an automatic boss
transition when armed before it starts. Selecting Preview advances the early
hold; it cannot restore the earlier loading stage already passed.

## Emergency hold

The Mac/Windows feature starts from an already spawned, living character. It
queues one controlled disconnect/recovery and arms a loading hold for the next
spawn. The disconnect is deferred to the native networking path, rather than
closing a socket from a rendering or mouse callback. Press/repeat suppression,
text-input checks and readiness/health guards limit accidental activation.

A remote observer seeing a character disappear is evidence about visibility,
not proof that every incoming hit was prevented. The server decides damage,
death, room availability and recovery destinations. A client cannot undo a
server-accepted death. There is no guaranteed maximum response time.

## Camera and UI

Free camera changes the local camera offset during an unspawned map preview;
it does not move the character or teleport followers. During recovery it waits
for a valid held world, then resumes. A different room starts from its native
camera offset/bounds. Finishing a hold, spawning or disabling camera mode ends
that selection.

Collapsing or hiding the UI only changes visibility. A hold, timer or reconnect
shortcut may remain active while every panel is hidden. Mac/Web F8 restores
hidden UI; their native/loading actions remain separate from the visibility state.

## Multiple clients

Native multibox instances exchange bounded local coordinator messages with
compatible peers. Health/status, shared controls, arming and reconnect commands
are separate operations. A shared room and fresh state are required for movement.
The focused client is the movement source; background clients use their own
input bindings. Turning controls off releases mirrored input.

The published snapshots in this repository broadcast Rush/Boss/Timed arming
through **Arm all clients**. Emergency hold remains local in those snapshots.
Mac and Windows use separate native groups. Web tabs share arming only within
the same browser profile/storage partition and origin.

## Session limits and destination

A preview can become stale after other players change rooms or the server ends
an instance. Recovery can return to another checkpoint or Eschaton. Neither a
six-minute timer nor a held preview reserves an SC chest, guarantees a particular
platform stage, prevents disconnections, or keeps an empty mission alive.

The plugin is intentionally explicit about these limits. Use its current state,
button labels and saved logs to distinguish a hold, a preview, normal spawning
and a server-initiated disconnect.

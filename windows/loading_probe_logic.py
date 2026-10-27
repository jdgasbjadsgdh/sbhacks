"""Windows loading state machine; independent of injection and UI (Python 3.6)."""
import time


class LoadingControl:
    def __init__(self, clock=time.monotonic, emit=None):
        self.clock = clock
        self.emit = emit or (lambda *args, **kwargs: None)
        self.state = 'idle'
        self.preset = 'any'
        self.held = None
        self.pending = None
        self.preview_requested = False
        self.fallback = False
        self.early_seconds = 360
        self.started = 0
        self.message = 'Choose a mode before entering the next map.'

    @staticmethod
    def same(c, held):
        return c and held and all(c.get(k) == held.get(k) for k in ('connection_id', 'socket', 'key'))

    @staticmethod
    def same_transport(c, held):
        return c and held and all(c.get(k) == held.get(k) for k in ('connection_id', 'socket'))

    def arm(self, c, preset='any'):
        if self.state in ('holding', 'waiting', 'reconnecting', 'finishing', 'preview_pending'):
            return False
        if not c or c['state'] != 3 or not c.get('key'):
            self.message = 'Enter a connected game before arming.'
            return False
        self.state, self.preset, self.held, self.pending = 'armed', preset, None, None
        self.preview_requested = False
        self.fallback = False
        self.started = self.clock()
        self.message = 'Armed: {}. Finish manually when ready.'.format(preset)
        self.emit('armed', preset=preset)
        return True

    def hold(self, c, kind):
        prior = self.held
        self.held = dict((k, c.get(k)) for k in ('connection_id', 'socket', 'key', 'game'))
        self.held['type'] = kind
        self.held['started'] = prior['started'] if prior else self.clock()
        self.state = 'holding'
        self.message = ('Waiting before map creation; Finish continues loading.' if kind == 22 else
                        'Map held. Finish reconnects for a fresh spawn.')
        if kind == 11 and self.preview_requested:
            self.message = 'Room preview ready. Reconnect when you want to spawn.'
        if kind == 11 and self.fallback:
            self.message = 'Fallback: early wait unavailable; map loaded.'
        self.emit('readiness_held', type=kind, world=c.get('world'), game=c.get('game'))

    def suppress(self, c, kind):
        """Called before native framing/encryption. True omits this empty message."""
        if not c or c['state'] != 3:
            return False
        if kind == 22:
            if self.preview_requested:
                return False
            if self.preset in ('rush', 'staged') and (self.state in ('armed', 'waiting') or
                                         self.state == 'holding' and self.held['type'] == 22):
                self.hold(c, 22)
                return True
            return False
        if kind != 11:
            return False
        if self.state == 'preview_pending':
            if c.get('key') and not c.get('player'):
                self.hold(c, 11)
                self.emit('room_preview_ready', world=c.get('world'))
                return True
            if c.get('player'):
                self.state = 'done'
                self.message = 'Character already present; preview hold did not start.'
            return False
        if self.state == 'finishing':
            self.state, self.pending = 'done', None
            self.message = 'Fresh map loading continued normally.'
            self.emit('world_after_early_finish', world=c.get('world'))
            return False
        if self.state == 'reconnecting':
            if self.same(c, self.held):
                return True
            self.state, self.pending = 'done', None
            self.message = 'Fresh readiness sent; server selects the spawn.'
            self.emit('fresh_world_ready', world=c.get('world'))
            return False
        if self.state in ('holding', 'waiting'):
            if not c.get('key') or c.get('player'):
                return False
            if self.held['type'] == 22:
                self.fallback = not self.preview_requested
                self.emit('early_hold_world_fallback')
            if not self.same(c, self.held) or self.held['type'] != 11:
                self.hold(c, 11)
            return True
        if self.state != 'armed' or not c.get('key') or c.get('player'):
            return False
        if self.preset == 'boss' and not any('_boss' in c.get(k, '') for k in ('zone', 'music')):
            return False
        if self.preset in ('rush', 'staged'):
            self.fallback = True
            self.emit('early_phase_absent_world_fallback')
        self.hold(c, 11)
        if self.preset in ('rush', 'staged'):
            self.message = 'Fallback: early wait unavailable; map loaded.'
        return True

    def frame(self, c):
        if self.state == 'holding':
            same = self.same_transport(c, self.held) if self.held['type'] == 22 else self.same(c, self.held)
            if not same or c['state'] != 3:
                self.state = 'waiting'
                self.message = 'Connection changed; hold retained until Finish.'
                self.emit('natural_loss_hold_retained')
            elif self.held['type'] == 11 and c.get('player'):
                self.state = 'done'
                self.message = 'Character appeared; free camera ended.'
                self.emit('unexpected_player')
        if (self.preset == 'staged' and not self.preview_requested and self.held and
                self.held['type'] == 22 and self.state in ('holding', 'waiting') and
                self.clock()-self.held['started'] >= self.early_seconds):
            self.preview(c)

    def preview_available(self):
        return bool(not self.pending and self.state in ('holding', 'waiting') and self.held and
                    self.held['type'] == 22 and not self.preview_requested)

    def preview(self, c):
        if not self.preview_available():
            return False
        self.preview_requested = True
        self.emit('room_preview_requested')
        return self.finish(c, preview=True)

    def finish(self, c, preview=False):
        if self.state in ('reconnecting', 'finishing', 'preview_pending') or self.pending:
            return False
        if not preview and self.preset == 'staged' and self.preview_available():
            return self.preview(c)
        if preview and (self.state == 'waiting' or not self.same_transport(c, self.held)):
            self.state = 'preview_pending'
            self.message = 'Waiting for a fresh map; spawn stays held.'
            return True
        if not c or c['state'] != 3:
            if self.state in ('holding', 'waiting'):
                self.state = 'preview_pending' if preview else 'reconnecting'
                self.message = ('Waiting for a fresh map; spawn stays held.' if preview else
                                'Finish accepted; next recovered load may spawn.')
                self.emit('finish_during_recovery')
                return True
            self.message = 'No active connection.'
            return False
        kind = 'asset' if self.state == 'holding' and self.held['type'] == 22 else 'reconnect'
        self.pending = dict((k, c.get(k)) for k in ('connection_id', 'socket', 'key', 'game'))
        self.pending['action'] = kind
        self.pending['preview'] = preview
        if not self.held:
            self.held = dict(self.pending)
        if kind == 'reconnect':
            self.state = 'reconnecting'
        self.message = 'Finish queued after the native receive callback returns.'
        self.emit('finish_requested', action=kind)
        return True

    def take_action(self, c, io_connection_id, io_ok):
        pending = self.pending
        if not pending:
            return None
        same = self.same_transport(c, pending) if pending['action'] == 'asset' else self.same(c, pending)
        if not same or c['state'] != 3:
            self.pending = None
            self.state = 'preview_pending' if pending.get('preview') else 'reconnecting'
            self.message = 'Waiting for a fresh recovered load.'
            self.emit('stale_finish_discarded')
            return None
        if io_connection_id != pending['connection_id'] or not io_ok:
            return None
        self.pending = None
        self.state = ('preview_pending' if pending.get('preview') else 'finishing') if pending['action'] == 'asset' else 'reconnecting'
        self.message = 'Finishing early load.' if pending['action'] == 'asset' else 'Reconnecting for a fresh spawn.'
        self.emit('finish_issued', action=pending['action'])
        return pending['action']

    def cancel(self, c):
        if self.state == 'armed':
            self.state = 'idle'
            self.message = 'Arm canceled.'
            self.emit('canceled')
        elif self.state == 'preview_pending':
            self.preview_requested = False
            self.pending = None
            self.state = 'finishing'
            self.message = 'Preview canceled; next map loads normally.'
        elif self.state in ('holding', 'waiting'):
            # Cancel finishes this hold; it must not start a staged preview.
            self.preset = 'any'
            self.finish(c)

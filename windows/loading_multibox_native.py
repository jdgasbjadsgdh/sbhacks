"""Use this client's own action bindings and native event handler on its UI thread."""
import ctypes
from loading_probe_x86 import call_two_thunk
from prepare_loading_probe import expected_entry


class NativeControls:
    def __init__(self, native):
        self.native = native;self.ffi = native.ffi
        addresses = {}
        for role in ('keyboard', 'mapping'):
            entry = native.target['functions'].get(role)
            if not entry:
                raise RuntimeError('Multibox symbols missing; reinstall and launch run.bat')
            address = native.base+entry['rva']
            expected = expected_entry(entry, native.target.get('image_base',native.base),native.base)
            if len(expected)!=24 or ctypes.string_at(address,24)!=expected:
                raise RuntimeError('Multibox '+role+' entry differs from this game build')
            addresses[role]=address
        self.keyboard = self.ffi.cast('int(*)(void *,int,int)', native.allocate(call_two_thunk(addresses['keyboard'])))
        self.get_mapping = self.ffi.cast('void *(*)(void)', addresses['mapping'])
        self.injected = {};self.stage = self.ffi.NULL
        self.events_sent=0;self.events_handled=0

    @staticmethod
    def valid(key):
        return 0 < key < 0x20000000 or 0x40000000 <= key < 0x40000400

    def keys(self):
        pointer = self.get_mapping()
        if pointer == self.ffi.NULL:
            return [[] for _ in range(14)]
        mapping = self.ffi.cast('struct InputMapping *',pointer)
        return [[k for k in (mapping.cik[a].primary,mapping.cik[a].secondary,mapping.cik[a].tertiary) if self.valid(k)] for a in range(14)]

    def held(self, lib, allowed):
        if not allowed:return 0
        n=self.ffi.new('int *');keys=lib.SDL_GetKeyboardState(n);mask=0
        for action, bindings in enumerate(self.keys()):
            for key in bindings:
                if key & 0x40000000:scan=key & 0x3fffffff
                else:
                    name={32:'Space',9:'Tab',13:'Return',27:'Escape'}.get(key,chr(key) if key<128 else '')
                    scan=lib.SDL_GetScancodeFromName(name.encode()) if name else 0
                if 0<scan<n[0] and keys[scan]:mask |= 1<<action
        return mask

    def apply(self, stage, mask):
        if stage == self.ffi.NULL:
            # A destroyed scene cannot receive releases. Forget its keys;
            # the next scene starts with a fresh native input handler.
            self.injected.clear();self.stage=stage;return
        if stage != self.stage:self.injected.clear();self.stage=stage
        bindings=self.keys()
        for action in list(self.injected):
            if not mask & (1<<action):self.event(stage,0,self.injected.pop(action))
        for action in range(14):
            if mask & (1<<action) and action not in self.injected and bindings[action]:
                key=bindings[action][0];self.event(stage,1,key);self.injected[action]=key

    def event(self,stage,down,key):
        handled=self.keyboard(stage,down,key)
        self.events_sent=getattr(self,'events_sent',0)+1
        self.events_handled=getattr(self,'events_handled',0)+int(bool(handled))

    def close(self):
        if self.stage != self.ffi.NULL:self.apply(self.stage,0)

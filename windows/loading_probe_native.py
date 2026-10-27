"""Native Windows x86 hooks for the loading plugin. No packet/RC4 manipulation."""
import ctypes
import hashlib
import json
import logging
import os
import platform
from loading_probe_x86 import callback_thunk, call_thunk
from prepare_loading_probe import expected_entry


class NativeLoading:
    def __init__(self, refs, ffi, lib, owner):
        if platform.system() != 'Windows' or ffi.sizeof('void *') != 4:
            raise RuntimeError('This adapter requires Windows 32-bit SBPE')
        self.refs, self.ffi, self.lib, self.owner = refs, ffi, lib, owner
        self.hooks, self.memory, self.callbacks, self.originals = [], [], [], {}
        self.closing = False
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        self.kernel.VirtualAlloc.restype = ctypes.c_void_p
        self.kernel.VirtualAlloc.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_ulong, ctypes.c_ulong]
        self.kernel.VirtualProtect.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_ulong, ctypes.POINTER(ctypes.c_ulong)]
        self.kernel.GetModuleHandleW.restype = ctypes.c_void_p
        self.kernel.GetModuleHandleW.argtypes = [ctypes.c_wchar_p]
        self.kernel.GetModuleFileNameW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_ulong]
        self.kernel.FlushInstructionCache.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t]
        filename = ctypes.create_unicode_buffer(32768)
        if not self.kernel.GetModuleFileNameW(None, filename, len(filename)):
            raise ctypes.WinError(ctypes.get_last_error())
        with open(os.path.join(refs.SCRIPTPATH, 'loading-probe-target.json')) as stream:
            target = json.load(stream)
        with open(filename.value, 'rb') as stream:
            actual = hashlib.sha256(stream.read()).hexdigest()
        if target.get('schema') != 1 or target.get('architecture') != 'x86' or target.get('game_sha256') != actual:
            raise RuntimeError('Game build differs from loading-probe-target.json; run the updated SBPE loader')
        base = self.kernel.GetModuleHandleW(None)
        self.target, self.base = target, base
        addresses = {}
        for role in ('send', 'io', 'error'):
            entry = target['functions'][role]
            address = base+entry['rva']
            expected = expected_entry(entry, target.get('image_base', base), base)
            if len(expected) != 24 or ctypes.string_at(address, 24) != expected:
                raise RuntimeError('Native {} method has changed or is already hooked'.format(role))
            addresses[role] = address
        # Keep all thunks/callbacks anchored for the process lifetime, including
        # after removal. A callback may still be returning through its thunk.
        refs.setdefault('_loading_native_keepalive', []).append(self)
        try:
            self.error = self.function(self.allocate(call_thunk(addresses['error'], True)), True, False)
            self.send = self.hook(addresses['send'], self.on_send, True, False)
            self.io = self.hook(addresses['io'], self.on_io, False, True)
        except Exception:
            self.remove_hooks()
            raise

    def allocate(self, code):
        address = self.kernel.VirtualAlloc(None, len(code), 0x3000, 0x04)
        if not address:
            raise ctypes.WinError(ctypes.get_last_error())
        ctypes.memmove(address, code, len(code))
        old = ctypes.c_ulong()
        if not self.kernel.VirtualProtect(address, len(code), 0x20, ctypes.byref(old)):
            raise ctypes.WinError(ctypes.get_last_error())
        if not self.kernel.FlushInstructionCache(ctypes.c_void_p(-1), address, len(code)):
            raise ctypes.WinError(ctypes.get_last_error())
        self.memory.append(address)
        return address

    def function(self, address, argument, boolean):
        signature = '{} (*)(void *{})'.format('unsigned char' if boolean else 'void', ', int' if argument else '')
        return self.ffi.cast(signature, address)

    def hook(self, address, callback, argument, boolean):
        signature = '{}(void *{})'.format('unsigned char' if boolean else 'void', ', int' if argument else '')
        wrapped = self.ffi.callback(signature, callback)
        self.callbacks.append(wrapped)
        pointer = int(self.ffi.cast('uintptr_t', wrapped))
        entry = self.allocate(callback_thunk(pointer, argument))
        hook = self.lib.subhook_new(self.ffi.cast('void *', address), self.ffi.cast('void *', entry), 0)
        if hook == self.ffi.NULL:
            raise RuntimeError('subhook allocation failed')
        self.hooks.append(hook)
        trampoline = self.lib.subhook_get_trampoline(hook)
        if trampoline == self.ffi.NULL:
            raise RuntimeError('Native hook needs an instruction-safe trampoline')
        original = self.function(self.allocate(call_thunk(int(self.ffi.cast('uintptr_t', trampoline)), argument)), argument, boolean)
        # Originals must be ready before installing the patch.
        self.originals['send' if argument else 'io'] = original
        if self.lib.subhook_install(hook) != 0 or not self.lib.subhook_is_installed(hook):
            raise RuntimeError('Native patch installation failed')
        return original

    def remove_hooks(self):
        for hook in reversed(self.hooks):
            if self.lib.subhook_is_installed(hook):
                self.lib.subhook_remove(hook)
        # Trampolines and callback thunks intentionally remain anchored: no
        # execution buffer can be freed while a native callback returns in it.

    def on_send(self, connection, kind):
        drop = False
        try:
            c = self.owner.current()
            if c and c['connection_id'] == int(self.ffi.cast('uintptr_t', connection)):
                drop = self.owner.control.suppress(c, kind)
        except Exception:
            logging.exception('Loading gate disabled after an exception; native send retained')
            self.owner.control.state = 'idle'
        if not drop:
            self.originals['send'](connection, kind)

    def on_io(self, connection):
        result = self.originals['io'](connection)
        try:
            c = self.owner.current()
            emergency=getattr(self.owner,'emergency',None)
            if emergency and emergency.take_action(c,int(self.ffi.cast('uintptr_t',connection)),bool(result)):
                # Same stock recovery path as normal Reconnect; retain the
                # explicit Rush arm so fresh readiness is held on recovery.
                try:self.error(c['gc'],2)
                except Exception:emergency.failed();raise
                return 0
            action = self.owner.control.take_action(c, int(self.ffi.cast('uintptr_t', connection)), bool(result))
            if action == 'asset':
                self.originals['send'](connection, 22)
            elif action == 'reconnect':
                # Receive dispatch is over. Let the stock GameClient destroy
                # the old world and choose the next load through its own path.
                self.error(c['gc'], 2)
                result = 0
            if self.closing and not self.owner.control.pending:
                self.remove_hooks()
        except Exception:
            logging.exception('Loading finish failed after native I/O')
        return result

    def close(self):
        self.closing = True
        control = self.owner.control
        if control.state in ('holding', 'waiting'):
            control.finish(self.owner.current())
        if not control.pending:
            self.remove_hooks()

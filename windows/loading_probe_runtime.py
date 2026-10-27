"""Bridge the already-compiled Windows CFFI mouse export, without rebuilding it."""
import logging


class MouseBridge:
    def __init__(self, refs, ffi, lib, mouse):
        self.refs, self.ffi, self.lib = refs, ffi, lib
        self.mouse, self.active, self.original = mouse, False, None
        self.callback = ffi.callback('void(int,int,int,int,void *)', self.dispatch)
        # Match SBPE's own API-mode conversion; its exported callable need
        # not be a cdata object accepted by an explicit ffi.cast().
        self.hook = lib.subhook_new(lib.hook_mouseButton, self.callback, 0)
        if self.hook == ffi.NULL:
            raise RuntimeError('Could not allocate the compiled-runtime mouse bridge')
        trampoline = lib.subhook_get_trampoline(self.hook)
        if trampoline == ffi.NULL:
            lib.subhook_free(self.hook)
            raise RuntimeError('Compiled-runtime mouse bridge has no safe trampoline')
        self.original = ffi.cast('void(*)(int,int,int,int,void *)', trampoline)
        refs.setdefault('_loading_mouse_keepalive', []).append(self)
        if lib.subhook_install(self.hook) != 0 or not lib.subhook_is_installed(self.hook):
            if lib.subhook_is_installed(self.hook):lib.subhook_remove(self.hook)
            raise RuntimeError('Could not install the compiled-runtime mouse bridge')
        self.active = True
        logging.info('Loading UI: compiled-runtime mouse bridge installed (window coordinates).')

    def dispatch(self, x, y, button, down, user):
        try:
            if self.active and self.mouse(x, y, button, down):
                return
        except Exception:
            logging.exception('Loading UI mouse callback failed; game input forwarded')
        self.original(x, y, button, down, user)

    def close(self):
        self.active = False
        if self.lib.subhook_is_installed(self.hook):self.lib.subhook_remove(self.hook)
        self.mouse = None
        # Native callback/trampoline stay anchored until process exit.

"""Manual single-client disconnect-and-hold; Python 3.6, no native ABI additions."""
import os
import shutil
import stat
import tempfile
import time
from loading_keybinds import replace_binding


def replace_hotkey(raw, name):
    """Replace one managed option, retaining every unrelated byte/comment."""
    return replace_binding(raw,'emergency_key',name)


class EmergencyHold:
    def __init__(self, owner, clock=time.monotonic):
        self.owner=owner;self.clock=clock;self.pending=None;self.before=None;self.phase='Ready'
        self.requested=0;self.last_trial=None;self.trial=0;self.spawned=0;self.last_hp=None
        self.arm_started=None
        self.message='Disconnect now; keep your next spawn held.';self.old_keys=set()
        self.visible=True;self.initialized=False;self.captured=False;self.pressed=None;self.binding=False;self.rects={}
        owner.config.option('emergency_enabled',True,'bool');owner.config.option('emergency_key','')

    def enabled(self):return self.owner.config.emergency_enabled

    @staticmethod
    def alive(c):return bool(c and c['state']==3 and c.get('player') and c.get('hp',0)>0)

    @staticmethod
    def same(c, other):return bool(c and other and all(c.get(k)==other.get(k) for k in ('connection_id','socket','key','game','player_id')))

    def emit(self,event,**values):self.owner.emit(event,trial=self.trial,**values)

    def cancel(self, message='Queued disconnect cancelled.'):
        if self.pending:
            if self.owner.control.state=='armed' and self.owner.control.started==self.pending['arm_started']:
                self.owner.control.cancel(self.owner.current())
            self.pending=None;self.phase='Not started';self.message=message
            self.emit('emergency_cancelled',reason=message)

    def start(self):
        c=self.owner.current();control=self.owner.control;now=self.clock()
        if (not self.enabled() or not self.owner.native or not self.alive(c) or self.pending or
                control.pending or control.state not in ('idle','done') or
                self.last_trial is not None and now-self.last_trial<10):
            self.message='Need a living character, no active hold; 10s between uses.';return False
        self.owner.arm('rush',local=True)
        if control.state!='armed' or control.preset!='rush':
            self.message='Could not arm or open the local log; no disconnect.';return False
        self.trial+=1;self.last_trial=self.requested=now;self.spawned=0;self.phase='Queued'
        self.before={k:c.get(k) for k in ('connection_id','socket','key','game','world','player_id','hp','maxhp')}
        self.arm_started=control.started
        self.pending=dict(self.before,arm_started=control.started);self.owner.camera=None
        self.message='One disconnect queued; the next spawn stays held.'
        self.emit('emergency_requested',hp_before=c['hp'],game=c['game'],world=c['world']);return True

    def take_action(self,c,connection_id,io_ok):
        pending=self.pending;control=self.owner.control
        if not pending or connection_id!=pending['connection_id']:return False
        if control.state in ('holding','waiting'):
            self.pending=None;self.phase='Waiting';self.message='Native loading overtook the request; no extra disconnect.';return False
        if not io_ok:
            self.pending=None;self.phase='Waiting';self.message='Native connection loss; the pending hold is retained.';return False
        if (not self.enabled() or not self.same(c,pending) or not self.alive(c) or
                control.state!='armed' or control.started!=pending['arm_started'] or
                self.clock()-self.requested>2):
            self.cancel('Player, room or connection changed; no disconnect issued.');return False
        self.pending=None;self.phase='Waiting';self.message='Reconnecting; the next spawn stays held.'
        self.emit('emergency_close_issued',request_to_close_ms=(self.clock()-self.requested)*1000,hp_before=self.before['hp'],hp_at_close=c['hp'])
        return True

    def frame(self,c):
        now=self.clock()
        if self.pending and self.owner.control.state in ('holding','waiting'):
            self.pending=None;self.phase='Waiting'
        elif self.pending and (not self.enabled() or now-self.requested>2):self.cancel('Queued request cancelled or expired.')
        if self.phase in ('Queued','Waiting','Holding') and self.before:
            if self.owner.control.state in ('holding','waiting'):
                if self.phase!='Holding':self.emit('emergency_recovery_held',elapsed_ms=(now-self.requested)*1000)
                self.phase='Holding';self.message='Spawn is held. Resume / reconnect when ready.'
            elif self.phase!='Queued' and self.alive(c):
                if self.owner.control.state=='armed' and self.owner.control.started==self.arm_started:self.owner.control.cancel(c)
                self.phase='Ready';self.spawned=now;self.last_hp=c['hp']
                self.message='Back in play: HP {} -> {}.'.format(self.before['hp'],c['hp'])
                self.emit('emergency_spawned',elapsed_ms=(now-self.requested)*1000,hp_before=self.before['hp'],hp_after=c['hp'],same_game=c['game']==self.before['game'])
            elif now-self.requested>90:
                self.phase='Ready';self.message='Observation ended; any loading hold stays active.'
        if self.spawned and now-self.spawned<5 and self.alive(c) and c['hp']!=self.last_hp:
            self.last_hp=c['hp'];self.emit('emergency_post_spawn_hp',hp=c['hp'])

    def conflict(self,name):
        editor=getattr(self.owner,'bindings',None)
        if editor:return bool(editor.conflict('emergency_key',name))
        code=self.scan(name)
        if not code:return True
        for key in (self.owner.config.panel_key,self.owner.config.arm_key,self.owner.config.finish_key):
            if key and self.scan(key)==code:return True
        cfg=getattr(self.owner.refs,'config',None)
        return bool(cfg and any(self.scan(value)==code for section in cfg.sections() for option,value in cfg.items(section,raw=True)
                               if not (section=='plugin_loading_probe' and option=='emergency_key')))

    def failed(self):
        if self.owner.control.state=='armed' and self.owner.control.started==self.arm_started:self.owner.control.cancel(self.owner.current())
        self.phase='Not started';self.message='Native reconnect failed; no automatic retry.'

    def scan(self,name):
        return self.owner.lib.SDL_GetScancodeFromName(name.encode()) if name else 0

    def persist(self,name):
        editor=getattr(self.owner,'bindings',None)
        if editor:
            saved=editor.save('emergency_key',name)
            if saved:self.message='Shortcut saved: '+(name or 'GUI only');self.binding=False
            else:self.message=editor.message
            return saved
        if name and self.conflict(name):self.message='That key is already used by another SBPE action.';return False
        path=self.owner.refs.CONFIGFILE
        with open(path,'rb') as source:raw=source.read()
        updated=replace_hotkey(raw,name)
        parent=os.path.dirname(os.path.abspath(path));fd,tmp=tempfile.mkstemp(prefix='.emergency-key-',dir=parent)
        try:
            with os.fdopen(fd,'wb') as stream:stream.write(updated)
            os.chmod(tmp,stat.S_IMODE(os.stat(path).st_mode))
            backup=os.path.join(parent,'loading-probe-backups');os.makedirs(backup,exist_ok=True)
            destination=os.path.join(backup,'emergency-key-{}-{}.ini'.format(time.time_ns() if hasattr(time,'time_ns') else int(time.time()*1000000),os.getpid()))
            shutil.copy2(path,destination);os.replace(tmp,path)
        finally:
            if os.path.exists(tmp):os.unlink(tmp)
        self.owner.config.emergency_key=name;self.message='Shortcut saved: '+(name or 'GUI only');self.binding=False;return True

    def input(self,keys,allowed):
        new=keys-self.old_keys;self.old_keys=set(keys)
        if not self.enabled():self.binding=False;return False
        if not allowed:return self.binding
        if self.binding:
            if 41 in new:self.binding=False;self.message='Key change cancelled.'
            elif 42 in new:
                try:self.persist('')
                except (OSError,ValueError) as error:self.message='Could not save shortcut: '+str(error);self.binding=False
            else:
                choices=sorted(key for key in new if key not in range(224,232))
                if choices:
                    name=self.owner.ffi.string(self.owner.lib.SDL_GetScancodeName(choices[0])).decode('utf-8')
                    try:
                        if name:self.persist(name)
                        else:self.message='That key is unavailable; choose another.'
                    except (OSError,ValueError) as error:self.message='Could not save shortcut: '+str(error);self.binding=False
            return True
        code=self.scan(self.owner.config.emergency_key)
        if self.enabled() and code in new and not self.conflict(self.owner.config.emergency_key) and not keys.intersection({224,226,227,228,230,231}):self.start()
        return False

    def resume(self):
        if self.pending:self.cancel()
        else:self.owner.finish()

    def layout(self):
        if not self.enabled():return None
        owner=self.owner;w,h=owner.refs.windowW,owner.refs.windowH
        if w<320 or h<300:return None
        s=min(max(1,owner.ui['scale'] if owner.ui else 1),(h-32)/252,(w-24)/324)
        if not self.initialized:self.visible=w>=760;self.initialized=True
        x,y=12,round(220*s) if h>=600*s else 20
        y=min(y,h-round(252*s)-12)
        panel=(x,y,round(324*s),round(252*s));tab=(x,y,round(180*s),round(28*s))
        self.rects={'start':(x+round(12*s),y+round(104*s),round(300*s),round(28*s)),
                    'resume':(x+round(12*s),y+round(156*s),round(145*s),round(28*s)),
                    'close':(x+round(167*s),y+round(156*s),round(145*s),round(28*s)),
                    'key':(x+round(12*s),y+round(210*s),round(300*s),round(24*s)),'tab':tab}
        return panel,tab,s

    def mouse(self,x,y,button,down):
        if button!=0:return False
        layout=self.layout()
        if not down and self.captured:
            self.captured=False;action,self.pressed=self.pressed,None
            if layout and action in self.rects and self.owner.inside(self.rects[action],x,y):
                if action=='start':self.start()
                elif action=='resume':self.resume()
                elif action=='close':self.visible=False
                elif action=='tab':self.visible=True
                elif action=='key':
                    editor=getattr(self.owner,'bindings',None)
                    if editor:editor.open('emergency_key')
                    else:self.binding=True;self.message='Press an unused key. Esc cancels; Backspace clears.'
            return True
        if not down or not layout or not self.owner.inside(layout[0] if self.visible else layout[1],x,y):return False
        self.captured=True;self.pressed=next((key for key,rect in self.rects.items() if key!='tab' and self.owner.inside(rect,x,y)),None) if self.visible else 'tab';return True

    def draw(self):
        layout=self.layout()
        if not layout:return
        owner=self.owner;panel,tab,s=layout;x,y,_,_=panel;old=owner.ui['scale'];owner.ui['scale']=s
        try:
            if not self.visible:
                owner.refs.XDL_FillRect(*tab,0xff29485a,1);owner.label('Emergency hold',x+10*s,y+5*s,13);return
            owner.refs.XDL_FillRect(*panel,0xff182430,1);owner.label('Emergency hold',x+12*s,y+12*s,16)
            owner.label(self.phase+' | '+(owner.config.emergency_key or 'GUI only'),x+12*s,y+38*s,12,width=300*s,color=0x88e8bd)
            for i,line in enumerate(owner.lines(self.message,max(12,round(12*s)),300*s)[:2]):owner.label(line,x+12*s,y+(62+i*16)*s,12)
            for key,label in [('start','Disconnect + hold'),('resume','Resume / reconnect'),('close','Close panel'),('key','Press a key...' if self.binding else 'Set hotkey: '+(owner.config.emergency_key or 'GUI only'))]:
                rect=self.rects[key];owner.refs.XDL_FillRect(*rect,0xff315b86 if key=='start' else 0xff215c53,1);owner.label(label,rect[0]+rect[2]/2,rect[1]+rect[3]/2,12,True,width=rect[2]-8*s)
            owner.label('This client only; no automatic health trigger.',x+12*s,y+136*s,12,width=300*s)
            owner.label('Close keeps the shortcut and hold active.',x+12*s,y+188*s,12,width=300*s)
            owner.label('Experimental: damage protection unverified.',x+12*s,y+236*s,12,width=300*s,color=0xffd185)
        finally:owner.ui['scale']=old

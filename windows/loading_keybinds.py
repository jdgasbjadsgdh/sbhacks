"""In-game key editor shared by loading and Emergency hold controls; Python 3.6."""
import os
import shutil
import stat
import tempfile
import time

ACTIONS=(('emergency_key','Emergency hold'),('panel_key','Loading panel'),
         ('arm_key','Arm selected hold'),('rush_key','Rush hold'),('boss_key','Boss hold'),
         ('preview_key','Preview room'),('finish_key','Resume / reconnect'),
         ('camera_key','Free camera'),('staged_key','Timed hold'),('cancel_key','Cancel hold'))
OPTIONS=tuple(option for option,_ in ACTIONS)
LABELS=dict(ACTIONS)


def replace_binding(raw,option,name):
    if option not in OPTIONS or '\n' in name or '\r' in name:raise ValueError('Invalid keybind option')
    newline=b'\r\n' if b'\r\n' in raw else b'\n';lines=raw.splitlines(True)
    inside=False;header=None;found=False;target=option.encode()
    for i,line in enumerate(lines):
        clean=line.strip()
        if clean.startswith(b'['):
            inside=clean.split(b']',1)[0].lower()==b'[plugin_loading_probe'
            if inside:header=i
        if inside and not clean.startswith((b'#',b';')) and clean.split(b'=',1)[0].strip().lower()==target:
            lines[i]=target+b' = '+name.encode('utf-8')+newline;found=True
    if not found:
        if header is None:raise ValueError('Loading plugin section missing; run the complete installer')
        if not lines[header].endswith((b'\n',b'\r')):lines[header]+=newline
        lines.insert(header+1,target+b' = '+name.encode('utf-8')+newline)
    return b''.join(lines)


def write_binding(path,option,name):
    with open(path,'rb') as source:raw=source.read()
    updated=replace_binding(raw,option,name);parent=os.path.dirname(os.path.abspath(path))
    fd,tmp=tempfile.mkstemp(prefix='.sbpe-keybind-',dir=parent)
    try:
        with os.fdopen(fd,'wb') as stream:stream.write(updated)
        os.chmod(tmp,stat.S_IMODE(os.stat(path).st_mode))
        backup=os.path.join(parent,'loading-probe-backups');os.makedirs(backup,exist_ok=True)
        destination=os.path.join(backup,'keybind-{}-{}.ini'.format(int(time.time()*1000000),os.getpid()))
        shutil.copy2(path,destination)
        with open(path,'rb') as source:
            if source.read()!=raw:raise ValueError('Config changed while saving; try again')
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)


class KeybindPanel:
    def __init__(self,owner):
        self.owner=owner;self.visible=False;self.target=None;self.page=0;self.old_keys=set();self.rects={};self.captured=set();self.pressed=None
        self.message='Click a key slot, then press a key.'
        for option in OPTIONS:
            if not hasattr(owner.config,option):owner.config.option(option,'')

    def scan(self,name):return self.owner.lib.SDL_GetScancodeFromName(name.encode()) if name else 0

    def conflict(self,option,name):
        code=self.scan(name)
        if not code:return 'That key is unavailable.'
        for other,label in ACTIONS:
            if other!=option and self.scan(getattr(self.owner.config,other))==code:return 'Already used by '+label+'. Clear that slot first.'
        cfg=getattr(self.owner.refs,'config',None)
        if cfg:
            for section in cfg.sections():
                for key,value in cfg.items(section,raw=True):
                    if section=='plugin_loading_probe' and key in OPTIONS:continue
                    if self.scan(value)==code:return 'That key is used by another SBPE tool.'
        return ''

    def save(self,option,name):
        if option not in OPTIONS:raise ValueError('Unknown keybind')
        issue=self.conflict(option,name) if name else ''
        if issue:self.message=issue;return False
        write_binding(self.owner.refs.CONFIGFILE,option,name)
        setattr(self.owner.config,option,name);self.target=None
        self.message=LABELS[option]+': '+(name or 'Unbound')+' saved.'
        status=getattr(self.owner,'save_status',None)
        if status:status()
        return True

    def open(self,target=None):
        self.visible=True;self.target=target
        self.old_keys=set(getattr(self.owner,'old_keys',set()))
        self.message='Press a key; Esc cancels, Backspace clears.' if target else 'Click a key slot, then press a key.'
        if target in OPTIONS:
            layout=self.layout()
            if layout:self.page=OPTIONS.index(target)//layout['count']

    def input(self,keys,allowed):
        new=keys-self.old_keys;self.old_keys=set(keys)
        if not self.visible:return False
        if not allowed:return True
        if 41 in new:
            if self.target:self.target=None;self.message='Key change cancelled.'
            else:self.visible=False
            return True
        if not self.target:return True
        try:
            if 42 in new:self.save(self.target,'')
            elif not keys.intersection({224,226,227,228,230,231}):
                choices=sorted(key for key in new if key not in {224,226,227,228,230,231})
                if choices:
                    name=self.owner.ffi.string(self.owner.lib.SDL_GetScancodeName(choices[0])).decode('utf-8')
                    if name:self.save(self.target,name)
        except (OSError,ValueError) as error:self.message='Could not save: '+str(error);self.target=None
        return True

    def layout(self):
        w,h=self.owner.refs.windowW,self.owner.refs.windowH
        if w<300 or h<300:return None
        s=min(max(1,self.owner.ui['scale'] if self.owner.ui else 1),(w-24)/460)
        pw,ph=min(round(540*s),w-24),min(round(560*s),h-24)
        x,y=(w-pw)//2,(h-ph)//2;pad=round(12*s);header=max(66,round(72*s));footer=max(92,round(96*s));pitch=max(30,round(32*s))
        count=max(1,min(len(ACTIONS),(ph-header-footer)//pitch));pages=(len(ACTIONS)+count-1)//count;self.page=min(self.page,pages-1)
        kw=max(88,round(148*s));self.rects={'close':(x+pw-pad-max(48,round(64*s)),y+pad,max(48,round(64*s)),max(24,round(26*s)))}
        rows=ACTIONS[self.page*count:(self.page+1)*count]
        for i,(option,label) in enumerate(rows):self.rects[option]=(x+pw-pad-kw,y+header+i*pitch,kw,pitch-4)
        bottom=y+ph-footer
        self.rects['previous']=(x+pad,bottom,round(64*s),max(24,round(26*s)))
        self.rects['next']=(x+pw-pad-round(64*s),bottom,round(64*s),max(24,round(26*s)))
        return dict(panel=(x,y,pw,ph),scale=s,pad=pad,header=header,pitch=pitch,footer=bottom,count=count,pages=pages,rows=rows)

    def mouse(self,x,y,button,down):
        layout=self.layout() if self.visible else None
        if not down and button in self.captured:
            self.captured.remove(button)
            if button!=0:return True
            action,self.pressed=self.pressed,None
            if layout and action in self.rects and self.owner.inside(self.rects[action],x,y):
                if action=='close':self.visible=False;self.target=None
                elif action=='previous':self.page=max(0,self.page-1);self.target=None
                elif action=='next':self.page=min(layout['pages']-1,self.page+1);self.target=None
                elif action in OPTIONS:self.target=action;self.message='Press a key; Esc cancels, Backspace clears.'
            return True
        if not down or not self.visible:return False
        self.captured.add(button)
        if button==0:self.pressed=next((key for key,rect in self.rects.items() if self.owner.inside(rect,x,y)),None) if layout else None
        return True

    def draw(self):
        if not self.visible:return
        layout=self.layout()
        if not layout:return
        owner=self.owner;p=layout['panel'];x,y,w,h=p;s=layout['scale'];pad=layout['pad'];old=owner.ui['scale'];owner.ui['scale']=s
        try:
            owner.refs.XDL_FillRect(0,0,owner.refs.windowW,owner.refs.windowH,0x99000000,1)
            owner.refs.XDL_FillRect(*p,0xff182430,1);owner.label('Keybinds',x+pad,y+pad,19,width=w-110*s)
            owner.label('Click a key slot to change it.',x+pad,y+42*s,12,width=w-2*pad)
            for i,(option,label) in enumerate(layout['rows']):
                r=self.rects[option];owner.label(label,x+pad,r[1]+4*s,13,width=r[0]-x-2*pad)
                owner.refs.XDL_FillRect(*r,0xff315b86 if option==self.target else 0xff29485a,1)
                owner.label('Press a key...' if option==self.target else getattr(owner.config,option) or 'Unbound',r[0]+r[2]/2,r[1]+r[3]/2,12,True,width=r[2]-6*s)
            for action,label in [('close','Close'),('previous','Prev'),('next','Next')]:
                r=self.rects[action];owner.refs.XDL_FillRect(*r,0xff315b86,1);owner.label(label,r[0]+r[2]/2,r[1]+r[3]/2,12,True,width=r[2]-6*s)
            owner.label('{}/{}'.format(self.page+1,layout['pages']),x+w/2,layout['footer']+12*s,12,True)
            lines=owner.lines(self.message,max(12,round(12*s)),w-2*pad)
            for i,line in enumerate(lines[:2]):owner.label(line,x+pad,layout['footer']+max(32,36*s)+i*max(16,16*s),12,width=w-2*pad)
            owner.label('Esc: cancel / close   Backspace: clear',x+pad,y+h-max(18,18*s),12,width=w-2*pad)
        finally:owner.ui['scale']=old

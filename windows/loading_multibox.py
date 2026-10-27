"""Sandboxie-capable multibox controls, rendered below Loading controls."""
import logging
import time
from loading_multibox_bus import Bus
from loading_multibox_native import NativeControls


def room_key(c,server):
    # ClientWorld.id identifies a local world object, not the shared room.
    # Match the same server/game/zone/floor identity as the Mac multibox.
    if not c or any(c.get(key) is None for key in ('game','zoneid','floor')):return None
    return [server.strip().lower(),c['game'],c['zoneid'],c['floor']]


class Multibox:
    def __init__(self, owner, ffi, lib, util):
        self.owner,self.ffi,self.lib,self.util=owner,ffi,lib,util
        self.bus=None;self.controls=None;self.error='';self.frame=None;self.me={};self.page=0
        self.captured=False;self.pressed=None;self.rects={};self.sync=None;self.next_jump=0;self.jump_until=0
        self.status='Starting local group';self.desired=0;self.next_status=0;self.saved_status=None
        cfg=owner.config
        cfg.option('multibox_enabled',True,'bool');cfg.option('multibox_port',47812,'int');cfg.option('multibox_group_key','')
        if not cfg.multibox_enabled:return
        try:self.bus=Bus(cfg.multibox_port,cfg.multibox_group_key)
        except Exception as error:self.error='Multibox unavailable: '+str(error)
        if owner.native:
            try:self.controls=NativeControls(owner.native)
            except Exception as error:self.error='Shared controls unavailable: '+str(error)
        else:self.error='Shared controls unavailable: native hooks did not initialize'
        if self.error:logging.warning(self.error)
        logging.info('Multibox initialized: loopback bus=%s; native controls=%s',bool(self.bus),bool(self.controls))

    def reserve(self):
        if not self.owner.config.multibox_enabled:return 0
        return min(250,max(0,self.owner.refs.windowH-380))

    def snapshot(self,c,allowed):
        s=dict(name='Client',valid=False,focus=False,held=0,hp=0,maxhp=0,world=None,hold=self.owner.control.state,
               x=0,y=0,w=0,h=0,controls=bool(self.controls),blocked=False)
        stage=self.owner.refs.stage[0]
        focused=self.lib.SDL_GetKeyboardFocus()==self.owner.refs.window_[0]
        s['focus']=bool(focused)
        blocked=getattr(self.owner,'game_input_blocked',None)
        s['blocked']=bool(stage==self.ffi.NULL or stage.textInputTarget or self.lib.SDL_IsTextInputActive()
                          or (blocked and blocked()) or getattr(getattr(self.owner,'bindings',None),'visible',False))
        if not c:return s
        s['world']=room_key(c,self.util.getstr(self.ffi.addressof(c['connection'],'hostname')))
        cw=c.get('cw')
        if cw is None or cw==self.ffi.NULL or not c['player']:return s
        p=self.ffi.cast('struct WorldObject *',cw.player).props
        s.update(valid=bool(p.hitpoints>0 and p.wmp>0 and p.hmp>0),hp=int(p.hitpoints),maxhp=int(p.maxhitpoints),
                 x=int(p.xmp),y=int(p.ymp),w=int(p.wmp),h=int(p.hmp))
        if p.displayname!=self.ffi.NULL:s['name']=self.util.getstr(p.displayname)[:32]
        if self.controls:s['held']=self.controls.held(self.lib, bool(allowed and s['valid'] and not s['blocked']))
        return s

    def update(self,c,allowed):
        if not self.bus:return
        self.me=self.snapshot(c,allowed)
        self.frame,commands=self.bus.tick(self.me)
        for request in commands:
            action=request.get('action') if isinstance(request,dict) else request
            if action.startswith('arm_'):self.owner.arm(action[4:],local=True)
            elif action=='reconnect':self.owner.finish()
            elif action=='sync':
                source=request.get('source') if isinstance(request,dict) else self.frame.get('source') if self.frame else None
                if source and source!=self.bus.id:self.sync=dict(source=source,until=time.monotonic()+20)
        desired=0;now=time.monotonic();frame=self.frame
        drive=frame.get('drive') if frame else None
        source=frame.get('source') if frame else None
        if self.sync and frame:
            source=self.sync['source']
            drive=next((peer for peer in frame.get('peers',[]) if peer['id']==self.sync['source']),None)
        same=bool(drive and self.me['valid'] and drive.get('valid') and self.me['world'] is not None and drive.get('world')==self.me['world'])
        if frame and frame.get('enabled') and frame.get('source')==source and source!=self.bus.id and same and not self.me['focus'] and drive.get('focus') and not drive.get('blocked') and not self.me['blocked']:
            desired=drive.get('held',0)&((1<<14)-1)
            if self.sync:
                if now>self.sync['until']:self.sync=None
                else:
                    a,b=self.me,drive;dx=(b['x']+b['w']/2)-(a['x']+a['w']/2);dy=b['y']-a['y']
                    overlap=max(0,min(a['x']+a['w'],b['x']+b['w'])-max(a['x'],b['x']))*max(0,min(a['y']+a['h'],b['y']+b['h'])-max(a['y'],b['y']))
                    if overlap>=.5*min(a['w']*a['h'],b['w']*b['h']):self.sync=None
                    else:
                        desired &= ~31
                        if abs(dx)>max(a['w'],b['w'])*.25:desired |= 2 if dx>0 else 1
                        if dy < -a['h']*.75 and now>=self.next_jump:self.jump_until=now+.35;self.next_jump=now+.8
                        if now<self.jump_until:desired |= 16
                        if dy>a['h'] and abs(dx)<a['w']:desired |= 8
        else:self.sync=None
        stage=self.owner.refs.stage[0]
        self.desired=desired
        if self.controls:self.controls.apply(stage,desired)
        self.status=self.summary()
        state=(self.status,self.error,bool(self.controls),getattr(self.controls,'events_sent',0),getattr(self.controls,'events_handled',0))
        if state!=self.saved_status and now>=self.next_status:
            if not self.saved_status or state[:3]!=self.saved_status[:3]:logging.info('Multibox: %s',self.status)
            self.next_status=now+2;self.saved_status=state
            save=getattr(self.owner,'save_status',None)
            if save:save()

    def summary(self):
        if self.error:return 'Input unavailable; see loading-status.txt'
        frame=self.frame
        if not frame:return 'Waiting for local group connection'
        if len(frame.get('peers',[]))<2:return 'Only this client; check group settings'
        if not frame.get('enabled'):return 'Controls OFF; click ON or Sync'
        drive=frame.get('drive')
        if not drive:return 'Focus a game window to lead'
        if not drive.get('controls'):return 'Focused client needs the complete update'
        if self.me.get('blocked') or drive.get('blocked'):return 'Paused for chat, menu or key settings'
        if not self.me.get('valid') or not drive.get('valid'):return 'Waiting for characters to spawn'
        if self.me.get('world') is None or drive.get('world')!=self.me.get('world'):return 'Other room; join the focused client'
        if self.me.get('focus'):return 'Leading; other clients follow this window'
        return 'Syncing toward leader' if self.sync else 'Following focused window'

    def diagnostics(self):
        return dict(bus_ready=bool(self.bus),native_controls_ready=bool(self.controls),
                    clients=len(self.frame.get('peers',[])) if self.frame else 0,
                    controls_on=bool(self.frame and self.frame.get('enabled')),status=self.summary(),
                    error=self.error,
                    events_sent=getattr(self.controls,'events_sent',0),events_handled=getattr(self.controls,'events_handled',0))

    def layout(self):
        if not self.owner.config.multibox_enabled:return None
        layout=self.owner.layout()
        if not layout:return None
        p=layout[0];x,y,w=p[0],p[1]+p[3]+8,p[2]
        available=self.owner.refs.windowH-y-12
        if available<140:return None
        peers=self.frame.get('peers',[]) if self.frame else []
        if not peers and self.bus:peers=[dict(self.me,id=self.bus.id)]
        peers=sorted(peers,key=lambda peer:peer['id'])
        count=max(1,int((available-100)//36));pages=max(1,(len(peers)+count-1)//count);self.page=min(self.page,pages-1)
        rows=peers[self.page*count:(self.page+1)*count]
        self.rects={};pad=10;half=(w-3*pad)//2;third=(w-4*pad)//3
        for i,name in enumerate(('toggle','sync','reconnect_all')):self.rects[name]=(x+pad+i*(third+pad),y+24,third,26)
        self.rects['previous']=(x+w-62,y+2,24,18);self.rects['next']=(x+w-34,y+2,24,18)
        for i,row in enumerate(rows):self.rects['reconnect:'+row['id']]=(x+w-100,y+100+i*36+2,90,24)
        return (x,y,w,100+len(rows)*36),rows,pages

    def mouse(self,x,y,button,down):
        if button!=0:return False
        layout=self.layout()
        if not down and self.captured:
            self.captured=False;pressed,self.pressed=self.pressed,None
            if layout and pressed in self.rects and self.owner.inside(self.rects[pressed],x,y):self.action(pressed)
            return True
        if not layout or not down or not self.owner.inside(layout[0],x,y):return False
        self.captured=True;self.pressed=next((key for key,rect in self.rects.items() if self.owner.inside(rect,x,y)),None)
        return True

    def action(self,key):
        if key=='previous':self.page=max(0,self.page-1);return
        if key=='next':self.page+=1;return
        if not self.bus:return
        if key=='toggle':self.bus.command('disable' if self.frame and self.frame.get('enabled') else 'enable')
        elif key=='reconnect_all':self.bus.command('reconnect')
        elif key.startswith('reconnect:'):self.bus.command('reconnect',key.split(':',1)[1])
        elif key in ('sync','arm_rush','arm_boss'):self.bus.command(key)

    def draw(self):
        layout=self.layout()
        if not layout:return
        p,rows,pages=layout;x,y,w,h=p;owner=self.owner;s=owner.ui['scale']
        # The auxiliary panel uses physical window coordinates and fixed,
        # readable 12px labels so health rows fit below the loading panel.
        old=owner.ui['scale'];owner.ui['scale']=1
        try:
            owner.refs.XDL_FillRect(*p,0xff182430,1)
            owner.label('Multibox | {}/{} | {} clients'.format(self.page+1,pages,len(self.frame['peers']) if self.frame else 1),x+10,y+3,12,width=w-90)
            enabled=bool(self.frame and self.frame.get('enabled'))
            names={'toggle':'Controls: ON' if enabled else 'Controls: OFF','sync':'Sync','reconnect_all':'Reconnect all',
                   'previous':'<','next':'>'}
            for key,rect in self.rects.items():
                label='Reconnect' if key.startswith('reconnect:') else names[key]
                owner.refs.XDL_FillRect(*rect,0xff315b86 if key.startswith('reconnect') else 0xff21675d,1)
                owner.label(label,rect[0]+rect[2]/2,rect[1]+rect[3]/2,12,True,width=rect[2]-6)
            for i,row in enumerate(rows):
                ry=y+98+i*36;label=row.get('name','Client')+(' (this)' if self.bus and row['id']==self.bus.id else '')
                owner.label(label+' | '+row.get('hold',''),x+10,ry,12,width=w-122)
                bw=w-122;ratio=max(0,min(1,row.get('hp',0)/max(1,row.get('maxhp',1))))
                owner.refs.XDL_FillRect(x+10,ry+21,bw,6,0xff303a40,1)
                owner.refs.XDL_FillRect(x+10,ry+21,round(bw*ratio),6,0xff40bf70,1)
            owner.label('Sync turns controls ON; focus the leader.',x+10,y+54,12,width=w-20)
            owner.label(self.summary(),x+10,y+73,12,width=w-20,color=0xffb0a0 if self.error else 0xb8dce2)
        finally:owner.ui['scale']=old

    def close(self):
        if self.controls:self.controls.close()
        if self.bus:self.bus.close()

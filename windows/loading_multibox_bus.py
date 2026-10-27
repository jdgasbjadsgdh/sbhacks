"""Authenticated loopback UDP bus across Sandboxie instances; Python 3.6.

Only bounded game state and a fixed command vocabulary are accepted. No file
sharing, named IPC exceptions, process injection or external network binding.
"""
import hashlib
import hmac
import json
import socket
import time
import uuid

COMMANDS = ('enable','disable','sync','reconnect','arm_any','arm_rush','arm_boss','arm_staged')


class Bus:
    def __init__(self, port, key, clock=time.monotonic):
        if not isinstance(key,str) or len(key)<16:raise ValueError('Multibox group_key must contain at least 16 characters')
        self.key=key.encode();self.clock=clock;self.id=uuid.uuid4().hex
        self.port=int(port);self.server=None;self.next_election=0
        self.sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);self.sock.bind(('127.0.0.1',0));self.sock.setblocking(False)
        self.peers={};self.outgoing={};self.pending={};self.server_seen={};self.executed={};self.received=[]
        self.enabled=False;self.frame=None;self.last_frame=0;self.next_send=0;self.next_broadcast=0;self.last_input=None;self.elect()

    def elect(self):
        if self.server:return
        now=self.clock()
        if now<self.next_election:return
        self.next_election=now+1
        s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        try:s.bind(('127.0.0.1',self.port));s.setblocking(False);self.server=s;self.enabled=False
        except OSError:s.close()

    def encode(self, data):
        body=json.dumps(data,separators=(',',':'),sort_keys=True).encode()
        return hmac.new(self.key,body,hashlib.sha256).hexdigest().encode()+b' '+body

    def decode(self, raw):
        if len(raw)>8192:return None
        try:
            signature,body=raw.split(b' ',1)
            if not hmac.compare_digest(signature,hmac.new(self.key,body,hashlib.sha256).hexdigest().encode()):return None
            data=json.loads(body.decode())
            return data if isinstance(data,dict) else None
        except (ValueError,UnicodeError):return None

    def send(self, source, data, target):
        raw=self.encode(data)
        if len(raw)>8192:return
        try:source.sendto(raw,target)
        except OSError:pass

    def command(self, action, target='all'):
        if action not in COMMANDS or not isinstance(target,str) or len(self.outgoing)>=32:return None
        key=uuid.uuid4().hex
        self.outgoing[key]={'type':'command','id':self.id,'command':key,'action':action,'target':target,'began':self.clock(),'sent':-10}
        return key

    def drain(self, sock):
        for _ in range(128):
            try:raw,address=sock.recvfrom(8193)
            except OSError:break
            if address[0]!='127.0.0.1':continue
            value=self.decode(raw)
            if value:yield value,address

    def tick(self, state):
        now=self.clock();self.elect()
        current_input=(state.get('held',0),state.get('focus',False))
        if now>=self.next_send or current_input!=self.last_input:
            self.next_send=now+.05
            self.last_input=current_input
            self.send(self.sock,{'type':'state','id':self.id,'state':state},('127.0.0.1',self.port))
        for key,request in list(self.outgoing.items()):
            if now-request['began']>2:del self.outgoing[key];continue
            if now-request['sent']>=.2:
                request['sent']=now
                self.send(self.sock,{k:v for k,v in request.items() if k not in ('began','sent')},('127.0.0.1',self.port))
        if self.server:
            dirty=False
            for data,address in self.drain(self.server):
                node=data.get('id');kind=data.get('type')
                if not isinstance(node,str) or len(node)!=32:continue
                if kind=='state' and isinstance(data.get('state'),dict):
                    s=data['state']
                    if not isinstance(s.get('held',0),int) or not 0<=s.get('held',0)<1<<14:continue
                    previous=self.peers.get(node)
                    if not previous or previous[0].get('held')!=s.get('held') or previous[0].get('focus')!=s.get('focus'):dirty=True
                    if len(self.peers)<16 or node in self.peers:self.peers[node]=(s,address,now)
                elif kind=='command' and node in self.peers and self.peers[node][1]==address:
                    command,action,target=data.get('command'),data.get('action'),data.get('target')
                    if not isinstance(command,str) or len(command)!=32 or action not in COMMANDS or not isinstance(target,str):continue
                    if command not in self.pending and command not in self.server_seen:
                        targets=list(self.peers) if target=='all' else [target] if target in self.peers else []
                        if action in ('enable','disable'):
                            self.enabled=action=='enable';targets=[]
                        # Sync is an explicit request for shared movement;
                        # it must not silently cancel because controls began
                        # OFF. Capture the requesting client as its target.
                        if action=='sync':self.enabled=True
                        self.pending[command]=[action,targets,now,node];self.server_seen[command]=now
                        dirty=True
                    self.send(self.server,{'type':'ack','command':command},address)
                elif kind=='done':
                    command=data.get('command')
                    if isinstance(command,str) and node in self.peers and self.peers[node][1]==address and command in self.pending:
                        if node in self.pending[command][1]:self.pending[command][1].remove(node)
            self.peers={key:v for key,v in self.peers.items() if now-v[2]<2}
            self.pending={key:v for key,v in self.pending.items() if v[1] and now-v[2]<2}
            self.server_seen={key:t for key,t in self.server_seen.items() if now-t<5}
            focused=[(key,v) for key,v in self.peers.items() if v[0].get('focus') and now-v[2]<.25]
            source=max(focused,key=lambda item:item[1][2])[0] if focused else None
            drive=self.peers[source][0] if source else None
            peers=[dict(v[0],id=key) for key,v in self.peers.items()]
            if dirty or now>=self.next_broadcast:
                self.next_broadcast=now+.05
                for node,(s,address,_) in self.peers.items():
                    commands=[dict(id=key,action=v[0],source=v[3]) for key,v in self.pending.items() if node in v[1]]
                    self.send(self.server,{'type':'frame','enabled':self.enabled,'source':source,'drive':drive,'peers':peers,'commands':commands},address)
        for data,address in self.drain(self.sock):
            if address!=('127.0.0.1',self.port):continue
            if data.get('type')=='ack' and isinstance(data.get('command'),str):self.outgoing.pop(data['command'],None)
            elif data.get('type')=='frame' and isinstance(data.get('peers'),list) and len(data['peers'])<=16:
                if not all(isinstance(peer,dict) and isinstance(peer.get('id'),str) for peer in data['peers']):continue
                if not isinstance(data.get('commands',[]),list):continue
                self.frame=data;self.last_frame=now
                for command in data.get('commands',[])[:32]:
                    if not isinstance(command,dict):continue
                    key,action=command.get('id'),command.get('action')
                    if not isinstance(key,str) or len(key)!=32 or action not in COMMANDS:continue
                    if key not in self.executed:
                        source=command.get('source')
                        self.received.append(dict(action=action,source=source) if action=='sync' and isinstance(source,str) else action)
                        self.executed[key]=now
                    self.send(self.sock,{'type':'done','id':self.id,'command':key},('127.0.0.1',self.port))
        self.executed={key:t for key,t in self.executed.items() if now-t<5}
        if now-self.last_frame>.4:self.frame=None
        commands,self.received=self.received,[]
        return self.frame,commands

    def close(self):
        self.sock.close()
        if self.server:self.server.close();self.server=None

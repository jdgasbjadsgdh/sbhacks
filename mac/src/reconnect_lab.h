/* Opt-in manual experiment, separate from ordinary Reconnect. Reuse the
 * verified deferred recovery path; never change HP, position or clocks. */
#ifndef SBPE_RECONNECT_LAB_H
#define SBPE_RECONNECT_LAB_H
#define DC_LAB_SECTION "plugin_reconnect_lab"
enum {DC_IDLE,DC_QUEUED,DC_WAIT,DC_HELD,DC_DONE,DC_CANCELLED};
struct DCLabSample {
    struct WorldClient *wc;struct ClientWorld *cw;struct ServerConnection *connection;
    struct Player *player;int socket,hp,maxhp;uint32_t game,world;
};
static struct {
    int state,hold_logged;
    unsigned trial;double requested,issued,last_trial,spawned_at,last_hp_sample;
    struct DCLabSample before,after;char result[160];
    uint8_t owned[512];
    double shortcut_refresh;char shortcut[64];
} dc_lab;
static int dc_lab_enabled(void){return getbool(DC_LAB_SECTION,"enabled",0);}
static int dc_lab_read(struct DCLabSample *s){
    struct WorldClient *wc=probe_world();struct Properties p;
    if(!wc||!wc->clientWorld||!wc->serverConnection||wc->serverConnection->state!=CONNECTED||wc->serverConnection->socket<0)return 0;
    struct ClientWorld *cw=wc->clientWorld;
    if(!cw->player||!read_memory(&((struct WorldObject*)cw->player)->props,&p,sizeof(p))||p.hitpoints<=0||p.maxhitpoints<=0)return 0;
    *s=(struct DCLabSample){wc,cw,wc->serverConnection,cw->player,wc->serverConnection->socket,p.hitpoints,p.maxhitpoints,cw->asWorld.props.gameid,cw->asWorld.id};return 1;
}
static int dc_lab_same(const struct DCLabSample *a,const struct DCLabSample *b){
    return a->wc==b->wc&&a->cw==b->cw&&a->connection==b->connection&&a->socket==b->socket&&a->player==b->player&&a->game==b->game&&a->world==b->world;
}
static void dc_lab_disarm_own(void){
    if(loading_probe.state==PROBE_ARMED&&loading_probe.preset==PROBE_RUSH)loading_probe.state=PROBE_IDLE;
}
static int dc_lab_confirm(void *connection);
static void dc_lab_cancel_queue(const char *why){
    if(dc_lab.state!=DC_QUEUED)return;
    if(probe_reconnect_cancel)probe_reconnect_cancel(dc_lab.before.connection,dc_lab_confirm);
    dc_lab.state=DC_CANCELLED;dc_lab_disarm_own();
    snprintf(dc_lab.result,sizeof(dc_lab.result),"%s",why);
    LOG("Loading test: disconnect lab trial=%u cancelled before close; reason=%s.",dc_lab.trial,why);
}
static int dc_lab_confirm(void *connection){
    struct DCLabSample current;
    if(dc_lab.state!=DC_QUEUED)return 0;
    if(!dc_lab_enabled()||paused||connection!=dc_lab.before.connection||!dc_lab_read(&current)||!dc_lab_same(&current,&dc_lab.before)||
       loading_probe.state!=PROBE_ARMED||loading_probe.preset!=PROBE_RUSH){
        dc_lab_cancel_queue("Player, room or connection changed; no close issued.");return 0;
    }
    dc_lab.state=DC_WAIT;dc_lab.issued=probe_clock();
    snprintf(dc_lab.result,sizeof(dc_lab.result),"Disconnect issued; waiting for held recovery.");
    LOG("Loading test: disconnect lab trial=%u manual close confirmed after native I/O; request_to_close_ms=%.3f hp_before=%d hp_at_close=%d game=%u world=%u. Rush arm retained; server disappearance and protection remain unverified.",
        dc_lab.trial,(dc_lab.issued-dc_lab.requested)*1000,dc_lab.before.hp,current.hp,current.game,current.world);
    return 1;
}
static int dc_lab_can_start(void){
    struct DCLabSample current;
    return dc_lab_enabled()&&!paused&&loading_probe_installed&&getbool("plugin_loading_probe","enabled",0)&&probe_reconnect_request&&probe_reconnect_cancel&&dc_lab_read(&current)&&
       !loading_probe.asset_finish&&loading_probe.state!=PROBE_ARMED&&loading_probe.state!=PROBE_HOLD&&loading_probe.state!=PROBE_WAIT&&loading_probe.state!=PROBE_RECONNECT&&
       dc_lab.state!=DC_QUEUED&&dc_lab.state!=DC_WAIT&&dc_lab.state!=DC_HELD&&
       (!dc_lab.trial||probe_clock()-dc_lab.last_trial>=10);
}
static const char *dc_lab_status(void){return dc_lab.result;}
static int dc_lab_start(void){
    double now=probe_clock();struct DCLabSample current;
    if(!dc_lab_can_start()||!dc_lab_read(&current)){
        snprintf(dc_lab.result,sizeof(dc_lab.result),"Need a living character, no active hold. Wait 10s between uses.");return 0;
    }
    int old_local=probe_group_local;probe_group_local=1;probe_preset=PROBE_RUSH;
    set_option("plugin_loading_probe","mode","manual");probe_arm();probe_group_local=old_local;
    if(loading_probe.state!=PROBE_ARMED){snprintf(dc_lab.result,sizeof(dc_lab.result),"Could not arm or open test log; no disconnect.");return 0;}
    dc_lab.before=current;dc_lab.state=DC_QUEUED;dc_lab.requested=dc_lab.last_trial=now;dc_lab.issued=dc_lab.spawned_at=0;dc_lab.hold_logged=0;++dc_lab.trial;
    LOG("Loading test: disconnect lab trial=%u requested manually; hp_before=%d maxhp=%d game=%u world=%u. One client only, no health trigger; no death rollback.",dc_lab.trial,current.hp,current.maxhp,current.game,current.world);
    if(!probe_reconnect_request(current.connection,dc_lab_confirm)){
        dc_lab_cancel_queue("Recovery queue busy; no disconnect issued.");return 0;
    }
    snprintf(dc_lab.result,sizeof(dc_lab.result),"Queued one disconnect; Rush stays armed.");return 1;
}
static int dc_lab_key_available(int sc){
    if(!key_from_name||sc<=0)return 0;
    if(controls_disconnect_reserved(sc))return 0;
    for(int a=0;a<CONTROL_COUNT;++a)if(a!=CONTROL_DISCONNECT)for(int c=0;c<3;++c)
        if(sc==key_from_name(control_keys[a][c]))return 0;
    for(int i=0;i<nbindings;++i)if(bindings[i].scancode==sc)return 0;
    return 1;
}
static int dc_lab_key_matches(int sc){
    if(!key_from_name||sc<=0)return 0;
    for(int c=0;c<3;++c)if(sc==key_from_name(control_keys[CONTROL_DISCONNECT][c]))return 1;
    return 0;
}
static const char *dc_lab_shortcut(void){
    double now=probe_clock();if(dc_lab.shortcut[0]&&now<dc_lab.shortcut_refresh)return dc_lab.shortcut;
    dc_lab.shortcut_refresh=now+.25;copystr(dc_lab.shortcut,sizeof(dc_lab.shortcut),"GUI only");
    for(int c=0;c<3;++c){const char *key=control_keys[CONTROL_DISCONNECT][c];
        if(key[0]&&strcmp(key,"None")&&dc_lab_key_available(key_from_name?key_from_name(key):0)){copystr(dc_lab.shortcut,sizeof(dc_lab.shortcut),key);break;}
    }return dc_lab.shortcut;
}
static void reconnect_lab_keys(const uint8_t *keys,int count,int allowed){
    int previous[3];memcpy(previous,control_previous[CONTROL_DISCONNECT],sizeof(previous));
    int pressed=controls_shortcut(keys,count,CONTROL_DISCONNECT,allowed&&!paused&&dc_lab_enabled());
    if(!pressed)return;
    for(int c=0;c<3;++c){int sc=key_from_name(control_keys[CONTROL_DISCONNECT][c]);
        if(sc>0&&sc<count&&keys[sc]&&!previous[c]&&dc_lab_key_available(sc)){dc_lab_start();return;}
    }
    snprintf(dc_lab.result,sizeof(dc_lab.result),"Shortcut already in use. Change Emergency hold in Controls > SBPE.");
}
static int reconnect_lab_consumes(struct Stage *st,int down,int key,int was_down){
    int sc=scancode_from_key?scancode_from_key(key):0;
    if(sc<=0||sc>=(int)sizeof(dc_lab.owned))return 0;
    if(!down&&dc_lab.owned[sc]){dc_lab.owned[sc]=0;return 1;}
    if(down&&dc_lab.owned[sc])return 1;
    if(down&&!was_down&&dc_lab_enabled()&&!paused&&st&&!st->textInputTarget&&!active_controls&&dc_lab_key_matches(sc)&&dc_lab_key_available(sc)){
        dc_lab.owned[sc]=1;return 1;
    }return 0;
}
static void reconnect_lab_frame(void){
    if(dc_lab.state==DC_DONE&&dc_lab.spawned_at){
        double now=probe_clock();struct DCLabSample current;
        if(now-dc_lab.spawned_at>5){dc_lab.spawned_at=0;return;}
        if(now-dc_lab.last_hp_sample>=.25&&dc_lab_read(&current)&&dc_lab_same(&current,&dc_lab.after)){
            dc_lab.last_hp_sample=now;
            if(current.hp!=dc_lab.after.hp){
                LOG("Loading test: disconnect lab trial=%u post-spawn HP changed after %.3f ms; hp=%d previous=%d. Observation only.",dc_lab.trial,(now-dc_lab.spawned_at)*1000,current.hp,dc_lab.after.hp);
                dc_lab.after=current;snprintf(dc_lab.result,sizeof(dc_lab.result),"After spawn: HP %d -> %d.",dc_lab.before.hp,current.hp);
            }
        }return;
    }
    if(dc_lab.state==DC_QUEUED){
        if(loading_probe.state==PROBE_HOLD||loading_probe.state==PROBE_WAIT){
            if(probe_reconnect_cancel)probe_reconnect_cancel(dc_lab.before.connection,dc_lab_confirm);
            dc_lab.state=DC_WAIT;
            LOG("Loading test: disconnect lab trial=%u native loss/loading overtook the queued request; no additional close issued.",dc_lab.trial);
        }else if(!dc_lab_enabled()||paused||probe_clock()-dc_lab.requested>2){
            if(probe_reconnect_cancel)probe_reconnect_cancel(dc_lab.before.connection,dc_lab_confirm);
            dc_lab_cancel_queue("Request cancelled or expired; no further close.");
        }
    }
    if(dc_lab.state!=DC_WAIT&&dc_lab.state!=DC_HELD)return;
    double elapsed=probe_clock()-dc_lab.requested;
    if(!dc_lab.hold_logged&&loading_probe.state==PROBE_HOLD){
        dc_lab.hold_logged=1;dc_lab.state=DC_HELD;
        snprintf(dc_lab.result,sizeof(dc_lab.result),"Held after %.2fs; observer must check disappearance.",elapsed);
        LOG("Loading test: disconnect lab trial=%u first held recovery after %.3f ms; ready_type=%d local_player=%s. This records local readiness only, not remote disappearance.",dc_lab.trial,elapsed*1000,loading_probe.ready_type,probe_world()&&probe_world()->clientWorld&&probe_world()->clientWorld->player?"present":"absent");
    }
    struct DCLabSample after;
    if(dc_lab_read(&after)){
        dc_lab.state=DC_DONE;dc_lab.after=after;dc_lab.spawned_at=dc_lab.last_hp_sample=probe_clock();
        snprintf(dc_lab.result,sizeof(dc_lab.result),"Spawned: HP %d -> %d. Check observer and room.",dc_lab.before.hp,after.hp);
        LOG("Loading test: disconnect lab trial=%u spawned after %.3f ms; hp_before=%d hp_after=%d same_game=%s game=%u world=%u. HP can change for other reasons; no survival claim inferred.",dc_lab.trial,elapsed*1000,dc_lab.before.hp,after.hp,after.game==dc_lab.before.game?"YES":"NO",after.game,after.world);
    }else if(elapsed>90){
        dc_lab.state=DC_DONE;snprintf(dc_lab.result,sizeof(dc_lab.result),"90s observation ended. Any loading hold stays active.");
        LOG("Loading test: disconnect lab trial=%u observation ended at 90s without a live spawned player; no readiness released or extra disconnect requested.",dc_lab.trial);
    }
}
#endif

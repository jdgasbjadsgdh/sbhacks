/* Exercise the real deferred I/O queue. No live socket or game is used. */
#define SBPE_RUSH_MAIN previous_rush_fixture_main
#include "test_rush_room_preview.c"
static unsigned lab_losses,group_calls;
static unsigned char lab_loss(void *p){
    assert(p==&connection&&network_loss_synthetic==2);
    assert(loading_probe.state==PROBE_ARMED&&loading_probe.preset==PROBE_RUSH&&!loading_probe.reconnect_issued);
    ++lab_losses;network_loss_observe(p,0);connection.state=4;connection.socket=-1;return 0;
}
static int group_spy(int preset){(void)preset;++group_calls;return 1;}
static void lab_context(void){
    manual_context();memset(&dc_lab,0,sizeof(dc_lab));lab_losses=group_calls=0;paused=0;probe_group_arm=NULL;
    set_option(DC_LAB_SECTION,"enabled","yes");set_option("plugin_loading_probe","enabled","yes");
    probe_reconnect_cancel=network_cancel_loading_reconnect;network_failure_io=lab_loss;
    cw.player=&actual_player;((struct WorldObject*)cw.player)->props.hitpoints=100;((struct WorldObject*)cw.player)->props.maxhitpoints=100;target();
}
#ifndef SBPE_EMERGENCY_MAIN
#define SBPE_EMERGENCY_MAIN main
#endif
int SBPE_EMERGENCY_MAIN(int argc,char **argv){
    previous_rush_fixture_main(argc,argv);
    lab_context();set_option(DC_LAB_SECTION,"enabled","no");assert(!dc_lab_start()&&!network_loading_reconnect.connection);
    lab_context();((struct WorldObject*)cw.player)->props.hitpoints=0;assert(!dc_lab_start()&&loading_probe.state==PROBE_IDLE);
    lab_context();probe_group_arm=group_spy;assert(dc_lab_start()&&!group_calls);probe_group_arm=NULL;
    assert(dc_lab.state==DC_QUEUED&&!lab_losses&&network_loading_reconnect.connection==&connection);
    assert(!dc_lab_start()&&dc_lab.trial==1);((struct WorldObject*)cw.player)->props.hitpoints=90;
    assert(network_do_io(&connection)==0&&lab_losses==1&&dc_lab.state==DC_WAIT&&loading_probe.state==PROBE_ARMED);
    assert(dc_lab.before.hp==100&&((struct WorldObject*)cw.player)->props.hitpoints==90);
    connection.state=CONNECTED;connection.socket=10;cw.asWorld.id++;cw.player=NULL;
    loading_probe_send(&connection,MT_WORLD_CREATED);reconnect_lab_frame();
    assert(loading_probe.state==PROBE_HOLD&&loading_probe.ready_type==MT_WORLD_CREATED&&dc_lab.state==DC_HELD&&!sends);
    fake_time+=30;reconnect_lab_frame();assert(lab_losses==1&&dc_lab.state==DC_HELD&&!network_loading_reconnect.connection);
    cw.player=&actual_player;((struct WorldObject*)cw.player)->props.hitpoints=85;reconnect_lab_frame();
    assert(dc_lab.state==DC_DONE&&strstr(dc_lab.result,"100 -> 85"));
    fake_time+=.3;((struct WorldObject*)cw.player)->props.hitpoints=80;reconnect_lab_frame();
    assert(dc_lab.after.hp==80&&strstr(dc_lab.result,"100 -> 80"));
    fake_time+=6;reconnect_lab_frame();assert(!dc_lab.spawned_at);
    lab_context();assert(dc_lab_start());((struct WorldObject*)cw.player)->props.hitpoints=0;
    assert(network_do_io(&connection)==1&&!lab_losses&&dc_lab.state==DC_CANCELLED&&loading_probe.state==PROBE_IDLE);
    lab_context();assert(dc_lab_start());cw.asWorld.id++;
    assert(network_do_io(&connection)==1&&!lab_losses&&dc_lab.state==DC_CANCELLED&&!network_loading_reconnect.connection);
    lab_context();assert(dc_lab_start());connection.socket++;assert(network_do_io(&connection)==1&&!lab_losses);
    fake_time+=2.1;reconnect_lab_frame();assert(dc_lab.state==DC_CANCELLED&&!network_loading_reconnect.connection);
    lab_context();assert(dc_lab_start());set_option(DC_LAB_SECTION,"enabled","no");reconnect_lab_frame();
    assert(dc_lab.state==DC_CANCELLED&&!network_loading_reconnect.connection&&!lab_losses);
    lab_context();assert(dc_lab_start());current=NULL;fixture_gc.worldClient=NULL;
    loading_probe_send(&connection,MT_PVID_LOADED);reconnect_lab_frame();
    assert(dc_lab.state==DC_HELD&&!lab_losses&&!network_loading_reconnect.connection);
    lab_context();loading_probe.state=PROBE_HOLD;assert(!dc_lab_start()&&loading_probe.state==PROBE_HOLD);
    lab_context();assert(network_request_loading_reconnect(&connection,probe_reconnect_begin));
    assert(!dc_lab_start()&&network_loading_reconnect.connection==&connection&&network_loading_reconnect.validate==probe_reconnect_begin&&!lab_losses);
    lab_context();physical_w=800;physical_h=600;int width=2400,height=1800;canvas_w=&width;canvas_h=&height;
    struct ProbeRect p,b[3],tab;assert(dc_lab_rects(&p,b,&tab));
    reconnect_lab_overlay();assert(width==2400&&height==1800);
    int x=b[2].x+5,y=b[2].y+5;assert(reconnect_lab_mouse(x,y,0,1,800,600));assert(reconnect_lab_mouse(x,y,0,0,800,600));assert(!dc_lab.visible);
    assert(reconnect_lab_mouse(tab.x+5,tab.y+5,0,1,800,600));assert(reconnect_lab_mouse(tab.x+5,tab.y+5,0,0,800,600));assert(dc_lab.visible);
    probe_record_close();puts("PASS: opt-in single-client disconnect lab; deferred exactly-once close, group bypass, HP logging without mutation, early/fallback hold, no automatic repeats, stale/dead/disabled cancellation, real queue cleanup and panel close/open/canvas restoration.");return 0;
}

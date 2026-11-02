/* Exercise explicit early-hold -> room-preview -> fresh spawn; offline only. */
#define SBPE_ANY_MAP_MAIN prior_loading_main
#include "test_any_map_loading.c"
#undef SBPE_ANY_MAP_MAIN
static void rush_early(void){
    manual_context();probe_preset=PROBE_RUSH;probe_arm();
    current=NULL;fixture_gc.worldClient=NULL;loading_probe_send(&connection,MT_PVID_LOADED);
    assert(loading_probe.state==PROBE_HOLD&&loading_probe.ready_type==MT_PVID_LOADED&&!sends);
}
static void describe(int shown,const char *part){
    char room[128],detail[128];assert(probe_room_description(room,sizeof(room),detail,sizeof(detail))==shown);
    assert(strstr(room,part)||strstr(detail,part));
}
#ifndef SBPE_RUSH_MAIN
#define SBPE_RUSH_MAIN main
#endif
int SBPE_RUSH_MAIN(int argc,char **argv){
    prior_loading_main(argc,argv);
    rush_early();describe(0,"not sent");assert(probe_room_preview_available());
    /* An old lobby still referenced by the game is never the future room. */
    current=&wc;fixture_gc.worldClient=&wc;describe(0,"not sent");
    current=NULL;fixture_gc.worldClient=NULL;
    fake_time+=600;loading_probe_frame();assert(!sends&&loading_probe.ready_type==MT_PVID_LOADED);
    probe_preview_room();assert(sends==1&&last_type==MT_PVID_LOADED&&probe_preview_pending()&&loading_probe.room_preview&&!manual_losses&&!network_loading_reconnect.connection);
    probe_preview_room();probe_manual_reconnect();assert(sends==1);describe(0,"fresh server-selected map");
    /* A stale world/connection callback cannot supply the displayed room. */
    current=&wc;fixture_gc.worldClient=&wc;struct ServerConnection old=connection;wc.serverConnection=&old;
    loading_probe_send(&old,MT_WORLD_CREATED);assert(probe_preview_pending()&&sends==1);describe(0,"not sent");wc.serverConnection=&connection;
    staged_world(&cathedral);cw.asWorld.props.floor=3;
    assert(sends==1&&loading_probe.state==PROBE_HOLD&&loading_probe.stage==PROBE_STAGE_PREVIEW&&!cw.player&&!loading_probe.staged_fallback);
    describe(1,"[boss]");describe(1,"Floor 4");assert(!probe_room_preview_available());
    struct STDString title;string(&title,"Star Cathedral");cw.asWorld.props.title=&title;describe(1,"Star Cathedral");cw.asWorld.props.title=NULL;
    cw.asWorld.props.floor=INT32_MAX;describe(1,"2147483648");cw.asWorld.props.floor=-1;describe(1,"Map #");
    /* Preview recovery never re-enters the early hold. */
    loading_probe_connection_lost(&connection,"fixture preview loss");connection.state=ERRORED;describe(0,"not sent");
    connection.state=CONNECTED;connection.socket++;loading_probe_send(&connection,MT_PVID_LOADED);assert(sends==2);
    cw.asWorld.id++;loading_probe_send(&connection,MT_WORLD_CREATED);assert(sends==2&&loading_probe.state==PROBE_HOLD&&loading_probe.stage==PROBE_STAGE_PREVIEW);describe(1,"[boss]");
    probe_manual_reconnect();assert(loading_probe.state==PROBE_RECONNECT&&!manual_losses&&sends==2);describe(0,"not sent");
    assert(!network_do_io(&connection)&&manual_losses==1);
    connection.state=CONNECTED;connection.socket++;cw.asWorld.id++;loading_probe_send(&connection,MT_PVID_LOADED);loading_probe_send(&connection,MT_WORLD_CREATED);
    assert(sends==4&&loading_probe.state==PROBE_RESULT&&loading_probe.reloaded);
    /* A preview requested during an early-hold loss waits for fresh native
       readiness instead of transmitting on an old socket. */
    rush_early();loading_probe_connection_lost(&connection,"fixture early loss");connection.state=ERRORED;connection.socket=-1;
    probe_preview_room();assert(probe_preview_pending()&&!sends&&!network_loading_reconnect.connection);
    connection.state=CONNECTED;connection.socket=11;loading_probe_send(&connection,MT_PVID_LOADED);staged_world(&lobby);
    assert(sends==1&&loading_probe.state==PROBE_HOLD);describe(1,"lobby");assert(strstr(loading_probe.result,"ESCHATON"));
    /* Cancel pending preview authorizes ordinary loading, without replay. */
    rush_early();probe_preview_room();probe_cancel();assert(!loading_probe.room_preview&&!probe_preview_pending()&&sends==1);
    staged_world(&cathedral);assert(sends==2&&loading_probe.state==PROBE_RESULT);
    /* If the server already supplied a player, report that the hold failed
       rather than labeling the spawned character as an unspawned preview. */
    rush_early();probe_preview_room();current=&wc;fixture_gc.worldClient=&wc;target();cw.asWorld.id++;cw.player=&actual_player;
    loading_probe_send(&connection,MT_WORLD_CREATED);
    assert(sends==2&&loading_probe.state==PROBE_RESULT&&!loading_probe.room_preview&&strstr(loading_probe.result,"already present"));describe(0,"not sent");
    /* Rush's original Finish loading remains a direct finish if preview was
       never requested. No premature preview before entry or after spawn. */
    manual_context();probe_preset=PROBE_RUSH;probe_arm();probe_preview_room();assert(!loading_probe.room_preview&&!sends&&loading_probe.state==PROBE_ARMED);
    rush_early();probe_manual_reconnect();staged_world(&cathedral);assert(sends==2&&loading_probe.state==PROBE_RESULT&&!loading_probe.room_preview);
    manual_context();probe_preset=PROBE_RUSH;probe_arm();staged_world(&cathedral);
    assert(loading_probe.state==PROBE_HOLD&&!loading_probe.room_preview);describe(1,"[boss]");assert(strstr(loading_probe.result,"fallback"));
    /* Actual button click advances early loading without releasing WORLD_CREATED. */
    rush_early();physical_w=800;physical_h=600;probe_gui_visible=1;probe_gui_captured=0;
    struct ProbeRect panel,buttons[PROBE_BUTTONS],tab;assert(probe_gui_rects(&panel,buttons,&tab));
    int x=buttons[7].x+buttons[7].w/2,y=buttons[7].y+buttons[7].h/2;
    assert(loading_probe_mouse(x,y,0,1,800,600)&&loading_probe_mouse(x,y,0,0,800,600));assert(probe_preview_pending()&&sends==1);
    if(argc>1){
        int w=2400,h=1800;canvas_w=&w;canvas_h=&h;
        rush_early();text_slot=0;gui_snapshot(argv[1],"rush-early-room-panel");
        probe_preview_room();staged_world(&cathedral);cw.asWorld.props.floor=3;text_slot=0;gui_snapshot(argv[1],"rush-preview-room-panel");
    }
    physical_w=physical_h=0;canvas_w=canvas_h=NULL;probe_record_close();
    puts("PASS: manual rush/early-boss hold, explicit room preview, exact-once asset continuation and blocked world readiness; no origin/stale room guesses, boss/title/floor labels, loss/recovery/cancel, ordinary finish retained, F10 fresh spawn, GUI click and draw fixtures.");return 0;
}

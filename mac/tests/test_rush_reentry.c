/* Real deferred I/O path with synthetic worlds and transport; no game launched. */
#define SBPE_RUSH_MAIN previous_rush_main
#include "test_rush_room_preview.c"
#undef SBPE_RUSH_MAIN
static unsigned retry_losses;
static unsigned char failed_io(void *p){assert(p==&connection);return 0;}
static unsigned char retry_failure(void *p){
    assert(p==&connection&&loading_probe.state==PROBE_WAIT&&!sends);
    ++retry_losses;connection.state=ERRORED;connection.socket=-1;return 0;
}
static void retry_hold(struct STDString *zone){
    manual_context();set_option("plugin_loading_probe","rush_reconnect","yes");
    probe_reconnect_cancel=network_cancel_loading_reconnect;
    probe_preset=PROBE_RUSH;probe_arm();network_failure_io=retry_failure;
    retry_losses=0;staged_world(zone);
    assert(loading_probe.state==PROBE_HOLD&&!sends&&!retry_losses);
    assert(network_loading_reconnect.connection==&connection&&loading_probe.rush_retry_attempted);
}
int main(int argc,char **argv){
    previous_rush_main(argc,argv);
    struct STDString bosses[8];const char *names[]={"sc_boss","forest_boss","ice_boss","cave_boss","jungle_boss","hulk_boss","dino_boss","temple_boss"};
    for(unsigned i=0;i<8;++i){
        string(&bosses[i],names[i]);retry_hold(&bosses[i]);
        loading_probe_send(&connection,MT_WORLD_CREATED);assert(!sends&&!retry_losses);
        assert(!network_do_io(&connection)&&retry_losses==1&&loading_probe.state==PROBE_WAIT);
        connection.state=CONNECTED;connection.socket=19;current=NULL;fixture_gc.worldClient=NULL;
        loading_probe_send(&connection,MT_PVID_LOADED);
        assert(loading_probe.ready_type==MT_PVID_LOADED&&loading_probe.state==PROBE_HOLD&&!sends);
        fake_time+=600;loading_probe_frame();assert(!sends&&!network_loading_reconnect.connection);
        probe_preview_room();assert(sends==1);staged_world(&bosses[i]);
        assert(loading_probe.state==PROBE_HOLD&&loading_probe.room_preview&&!network_loading_reconnect.connection);
    }
    /* If the recovered server skips assets too, remain a visible fallback;
       never deliberately close repeatedly, even across later natural losses. */
    retry_hold(&cathedral);assert(!network_do_io(&connection));
    connection.state=CONNECTED;connection.socket=20;staged_world(&cathedral);
    assert(loading_probe.state==PROBE_HOLD&&!network_loading_reconnect.connection&&!sends);
    loading_probe_connection_lost(&connection,"fixture loss");connection.socket++;staged_world(&cathedral);
    assert(!network_loading_reconnect.connection&&!sends);
    /* Finish and Cancel win over queued early retry. A single ordinary finish
       remains queued, with fresh readiness authorized after its close. */
    retry_hold(&cathedral);network_failure_io=manual_failure;probe_manual_reconnect();
    assert(network_loading_reconnect.validate==probe_reconnect_begin&&!loading_probe.rush_retry_pending);
    assert(!network_do_io(&connection)&&manual_losses==1);
    retry_hold(&cathedral);network_failure_io=manual_failure;probe_cancel();
    assert(network_loading_reconnect.validate==probe_reconnect_begin);
    assert(!network_do_io(&connection)&&manual_losses==1);
    /* Socket/world/player changes or disabling before the deferred callback
       cannot close a newer or spawned connection. */
    retry_hold(&cathedral);cw.asWorld.id++;assert(network_do_io(&connection)&&!retry_losses);
    retry_hold(&cathedral);connection.socket++;assert(network_do_io(&connection)&&!retry_losses);
    retry_hold(&cathedral);cw.player=&actual_player;assert(network_do_io(&connection)&&!retry_losses);
    retry_hold(&cathedral);set_option("plugin_loading_probe","enabled","no");assert(network_do_io(&connection)&&!retry_losses);
    set_option("plugin_loading_probe","enabled","yes");
    /* Natural I/O failure wins; no second synthetic loss is issued. */
    retry_hold(&cathedral);network_continue_io=failed_io;assert(!network_do_io(&connection)&&!retry_losses&&!network_loading_reconnect.connection);
    probe_record_close();puts("PASS: any-boss Rush early reentry, one deferred reconnect, no readiness release or retry loop; early recovery, repeated fallback/loss, manual finish/cancel, stale world/socket/player/disable and native failure races.");return 0;
}

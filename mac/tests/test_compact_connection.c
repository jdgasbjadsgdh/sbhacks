/* Current compact Connection flow; synthetic worlds/clocks and loopback fixtures only. */
#define SBPE_EMERGENCY_MAIN inherited_connection_main
#include "test_reconnect_lab.c"
#undef SBPE_EMERGENCY_MAIN
static void compact_click(struct ProbeRect r){
    assert(loading_probe_mouse(r.x+r.w/2,r.y+r.h/2,0,1,physical_w,physical_h));
    assert(loading_probe_mouse(r.x+r.w/2,r.y+r.h/2,0,0,physical_w,physical_h));
}
static void compact_setup(void){
    lab_context();probe_gui_visible=1;probe_gui_captured=0;probe_gui_pressed=-1;
    probe_clients_height=probe_below_height=NULL;probe_group_arm=NULL;
    physical_w=800;physical_h=600;
}
static unsigned char rush_retry_loss(void *c){
    assert(c==&connection&&network_loss_synthetic==2&&loading_probe.state==PROBE_WAIT);
    ++manual_losses;network_loss_observe(c,0);connection.state=ERRORED;connection.socket=-1;return 0;
}
static void compact_capture(const char *folder,const char *name){
    int w=physical_w*2,h=physical_h*2;canvas_w=&w;canvas_h=&h;render_pixel_ratio=1;text_slot=0;
    if(folder){char path[4096];snprintf(path,sizeof(path),"%s/%s.svg",folder,name);preview=fopen(path,"w");assert(preview);
        fprintf(preview,"<svg xmlns='http://www.w3.org/2000/svg' width='%d' height='%d'><rect width='%d' height='%d' fill='#09233a'/>\n",physical_w,physical_h,physical_w,physical_h);}
    loading_probe_overlay();assert(w==physical_w*2&&h==physical_h*2);
    if(preview){fputs("</svg>\n",preview);fclose(preview);preview=NULL;}canvas_w=canvas_h=NULL;
}
int main(int argc,char **argv){
    inherited_connection_main(argc,argv);const char *folder=argc>1?argv[1]:NULL;
    compact_setup();struct ProbeRect p,b[PROBE_BUTTONS],tab;assert(probe_gui_rects(&p,b,&tab));
    assert(p.w==328&&p.h==284&&PROBE_BUTTONS==6);
    for(int i=0;i<PROBE_BUTTONS;++i){
        assert(b[i].x>=p.x&&b[i].y>=p.y&&b[i].x+b[i].w<=p.x+p.w&&b[i].y+b[i].h<=p.y+p.h);
        for(int j=i+1;j<PROBE_BUTTONS;++j)assert(b[i].x+b[i].w<=b[j].x||b[j].x+b[j].w<=b[i].x||b[i].y+b[i].h<=b[j].y||b[j].y+b[j].h<=b[i].y);
    }
    assert(b[PROBE_DISCONNECT_BUTTON].x>b[PROBE_RUSH_BUTTON].x&&b[PROBE_DISCONNECT_BUTTON].y==b[PROBE_RUSH_BUTTON].y);
    compact_capture(folder,"compact-ready");
    /* A saved legacy selection never makes F9 arm Boss/Timed again. */
    for(int preset=PROBE_ANY;preset<=PROBE_STAGED;++preset){
        compact_setup();probe_preset=preset;probe_f9=0;uint8_t keys[128]={0};keys[66]=1;
        loading_probe_keys(keys,128,1);assert(loading_probe.state==PROBE_ARMED&&loading_probe.preset==PROBE_RUSH);
    }
    /* Legacy multibox commands are translated locally to the same Rush flow. */
    for(int preset=PROBE_ANY;preset<=PROBE_STAGED;++preset){compact_setup();assert(mb_arm_local(preset)&&loading_probe.preset==PROBE_RUSH);}
    /* Ordinary next-room loading and SC after the last generator use the same
       early gate, with no requirement for a live WorldClient or a boss label. */
    for(int sc=0;sc<2;++sc){
        compact_setup();assert(probe_gui_rects(&p,b,&tab));compact_click(b[PROBE_RUSH_BUTTON]);
        assert(loading_probe.state==PROBE_ARMED&&loading_probe.preset==PROBE_RUSH);
        current=NULL;fixture_gc.worldClient=NULL;loading_probe_send(&connection,MT_PVID_LOADED);
        assert(loading_probe.state==PROBE_HOLD&&loading_probe.ready_type==MT_PVID_LOADED&&!sends);
        fake_time+=120;loading_probe_frame();assert(!sends&&!network_loading_reconnect.connection);
        compact_capture(folder,sc?"compact-sc-rush":"compact-room-rush");
        if(sc){
            compact_click(b[PROBE_PREVIEW_BUTTON]);assert(sends==1&&probe_preview_pending());double start=loading_probe.preview_started;
            fake_time+=2;cw.player=NULL;staged_world(&cathedral);assert(loading_probe.state==PROBE_HOLD&&loading_probe.room_preview&&sends==1&&!cw.player);
            assert(probe_preview_remaining()>7.99&&probe_preview_remaining()<8.01);
            compact_capture(folder,"compact-sc-preview");
            loading_probe_connection_lost(&connection,"fixture preview loss");connection.state=ERRORED;connection.socket=-1;
            fake_time+=6;connection.state=CONNECTED;connection.socket=20;loading_probe_send(&connection,MT_PVID_LOADED);cw.asWorld.id++;
            loading_probe_send(&connection,MT_WORLD_CREATED);assert(loading_probe.state==PROBE_HOLD&&loading_probe.preview_started==start);
            assert(probe_preview_remaining()>1.99&&probe_preview_remaining()<2.01&&sends==2);
            fake_time+=3;loading_probe_frame();assert(probe_preview_remaining()==0&&sends==2&&!network_loading_reconnect.connection);
            /* Countdown warns; it never auto-connects or refreshes. */
            network_failure_io=manual_failure;compact_click(b[PROBE_CONNECT_BUTTON]);
            assert(loading_probe.state==PROBE_RECONNECT&&network_loading_reconnect.connection==&connection);
            assert(!network_do_io(&connection)&&manual_losses==1);
        }else{
            compact_click(b[PROBE_CONNECT_BUTTON]);assert(sends==1&&loading_probe.asset_finish&&!network_loading_reconnect.connection);
            cw.player=NULL;staged_world(&cave);assert(sends==2&&loading_probe.state==PROBE_RESULT&&!loading_probe.room_preview);
        }
    }
    /* When a same-server room omits assets, Rush tries one deferred native
       reconnect to obtain the early gate. There is no periodic refresh. */
    compact_setup();set_option("plugin_loading_probe","rush_reconnect","yes");network_failure_io=rush_retry_loss;
    probe_preset=PROBE_RUSH;probe_arm();cw.player=NULL;staged_world(&cathedral);
    assert(loading_probe.rush_retry_pending&&network_loading_reconnect.connection==&connection&&!sends);
    assert(!network_do_io(&connection)&&manual_losses==1&&loading_probe.state==PROBE_WAIT);
    connection.state=CONNECTED;connection.socket=22;current=NULL;fixture_gc.worldClient=NULL;
    loading_probe_send(&connection,MT_PVID_LOADED);assert(loading_probe.ready_type==MT_PVID_LOADED&&!sends);
    fake_time+=30;loading_probe_frame();assert(!network_loading_reconnect.connection&&!sends&&manual_losses==1);
    /* If recovery omits assets too, the preview fallback stays held once. */
    staged_world(&cathedral);assert(loading_probe.ready_type==MT_WORLD_CREATED&&!network_loading_reconnect.connection&&!sends);
    fake_time+=30;loading_probe_frame();assert(!network_loading_reconnect.connection&&!sends&&manual_losses==1);
    compact_capture(folder,"compact-fallback");
    /* Finishing a fallback before its queued retry must not leave an extra close. */
    compact_setup();set_option("plugin_loading_probe","rush_reconnect","yes");probe_preset=PROBE_RUSH;probe_arm();cw.player=NULL;staged_world(&cathedral);
    assert(loading_probe.rush_retry_pending);probe_manual_reconnect();assert(!loading_probe.rush_retry_pending);
    network_failure_io=manual_failure;assert(!network_do_io(&connection)&&manual_losses==1);
    /* The relocated button starts the existing guarded, exact-once close. */
    compact_setup();assert(probe_gui_rects(&p,b,&tab));compact_click(b[PROBE_DISCONNECT_BUTTON]);
    assert(dc_lab.state==DC_QUEUED&&loading_probe.state==PROBE_ARMED&&loading_probe.preset==PROBE_RUSH);
    assert(!network_do_io(&connection)&&lab_losses==1&&dc_lab.state==DC_WAIT);
    /* A short/narrow window and Retina drawing keep all controls in bounds. */
    compact_setup();for(int ratio=1;ratio<=2;++ratio)for(int width=280;width<=1280;width+=200){
        render_pixel_ratio=ratio;physical_w=width;physical_h=304;text_slot=0;int w=width*ratio,h=608;canvas_w=&w;canvas_h=&h;
        loading_probe_overlay();assert(w==width*ratio&&h==608);
    }
    compact_setup();physical_w=280;physical_h=304;
    compact_capture(folder,"compact-narrow");
    /* The obsolete left panel no longer captures a gameplay click. */
    compact_setup();forwarded_clicks=0;void *window=NULL;window_ptr=&window;get_window_size=gui_window;original_button=click_passthrough;
    int w=800,h=600;canvas_w=&w;canvas_h=&h;
    mouse_button(15,150,0,1,NULL);mouse_button(15,150,0,0,NULL);assert(forwarded_clicks==2);
    canvas_w=canvas_h=NULL;window_ptr=NULL;get_window_size=NULL;physical_w=physical_h=0;probe_record_close();
    puts("PASS: compact six-button panel; Rush-only F9/legacy multibox; next-room/SC early hold; explicit preview with non-resetting 10s warning countdown; finish; one deferred early-phase retry; fallback without a loop; integrated disconnect; short/narrow/Retina bounds; obsolete left-panel passthrough.");
}

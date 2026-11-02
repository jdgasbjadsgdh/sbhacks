/* Exercise actual native render/mouse/key handlers without a live game. */
#define SBPE_EMERGENCY_MAIN previous_emergency_main
#include "test_reconnect_lab.c"
#undef SBPE_EMERGENCY_MAIN
static int forwarded;
static void hide_window(void *window,int *w,int *h){(void)window;*w=1280;*h=800;}
static void hide_game_mouse(int x,int y,int button,int down,void *data){(void)x;(void)y;(void)button;(void)down;(void)data;++forwarded;}
static void draw_disconnect_ui(void){
    gui_rectangles=gui_texts=text_slot=0;
    loading_probe_overlay();reconnect_lab_overlay();multibox_connections_overlay();multibox_overlay();
}

int main(int argc,char **argv){
    previous_emergency_main(argc,argv);
    lab_context();loading_probe_installed=1;set_option("plugin_loading_probe","enabled","yes");
    connectivity_ui_hidden=0;physical_w=1280;physical_h=800;render_pixel_ratio=1;
    int w=1280,h=800;canvas_w=&w;canvas_h=&h;
    create_text=gui_make_text;query_texture=gui_query;draw_texture=gui_texture;fill_rect=gui_rectangle;
    dc_lab.initialized=1;dc_lab.visible=1;probe_gui_visible=1;
    memset(&mb,0,sizeof(mb));mb.fd=-1;mb.inited=1;mb.role=MB_LEADER;mb.instance=1;mb.enabled_override=1;
    mb.self=(struct MultiboxState){.instance=1,.leader=1,.valid=1,.hp=100,.maxhp=100,.name="Main"};
    probe_clients_height=mb_connection_height;probe_below_height=mb_below_height;
    draw_disconnect_ui();assert(gui_rectangles>0&&gui_texts>0&&w==1280&&h==800);
    void *window=NULL;window_ptr=&window;get_window_size=hide_window;original_button=hide_game_mouse;
    struct ProbeRect panel,buttons[PROBE_BUTTONS],tab;assert(probe_gui_rects(&panel,buttons,&tab));
    struct ProbeRect hide=probe_hide_ui_rect(panel);int x=hide.x+hide.w/2,y=hide.y+hide.h/2;
    assert(hide.x>=panel.x&&hide.x+hide.w<=panel.x+panel.w);

    /* Releasing outside does not activate the button. */
    mouse_button(x,y,0,1,NULL);mouse_button(5,5,0,0,NULL);assert(!connectivity_ui_hidden&&!forwarded);
    probe_preset=PROBE_RUSH;probe_arm();loading_probe_send(&connection,MT_PVID_LOADED);
    assert(loading_probe.state==PROBE_HOLD);int ready=loading_probe.ready_type;double started=loading_probe.started;
    unsigned before=sends;mouse_button(x,y,0,1,NULL);mouse_button(x,y,0,0,NULL);
    assert(connectivity_ui_hidden&&!forwarded&&loading_probe.state==PROBE_HOLD&&loading_probe.ready_type==ready&&loading_probe.started==started&&sends==before);
    assert(dc_lab.visible&&mb_local_enabled());
    draw_disconnect_ui();assert(!gui_rectangles&&!gui_texts&&w==1280&&h==800);
    /* Tabs must disappear too, and hidden panels must not eat game clicks. */
    probe_gui_visible=dc_lab.visible=0;draw_disconnect_ui();assert(!gui_rectangles&&!gui_texts);
    mouse_button(x,y,0,1,NULL);mouse_button(x,y,0,0,NULL);assert(forwarded==2);
    dc_lab.captured=1;assert(reconnect_lab_mouse(x,y,0,0,1280,800)&&!dc_lab.captured);
    mb.captured=1;assert(multibox_mouse(x,y,0,0,1280,800)&&!mb.captured);
    probe_gui_captured=1;assert(loading_probe_mouse(x,y,0,0,1280,800)&&!probe_gui_captured);

    /* Focus/chat ownership and held-key guards remain intact. F8 restores
     * rather than immediately toggling the newly restored panel closed. */
    uint8_t keys[128]={0};probe_f8=0;keys[65]=1;
    loading_probe_keys(keys,128,0);loading_probe_keys(keys,128,1);assert(connectivity_ui_hidden);
    keys[65]=0;loading_probe_keys(keys,128,1);keys[65]=1;loading_probe_keys(keys,128,1);
    assert(!connectivity_ui_hidden&&probe_gui_visible&&!dc_lab.visible&&loading_probe.state==PROBE_HOLD);
    loading_probe_keys(keys,128,1);assert(probe_gui_visible);
    draw_disconnect_ui();assert(gui_rectangles>0&&gui_texts>0);
    /* Emergency activation still works while its interface is hidden. */
    lab_context();connectivity_ui_hidden=1;assert(dc_lab_start());
    assert(connectivity_ui_hidden&&dc_lab.state==DC_QUEUED&&loading_probe.state==PROBE_ARMED);
    dc_lab_cancel_queue("fixture cleanup");connectivity_ui_hidden=0;
    canvas_w=canvas_h=NULL;
    puts("PASS: hide-all button, drag/release guards, no panel/tab draws or hidden hit boxes, captured mouse-up cleanup, unchanged hold/multibox state, F8 restore with focus/repeat guards and hidden Emergency activation.");
    return 0;
}

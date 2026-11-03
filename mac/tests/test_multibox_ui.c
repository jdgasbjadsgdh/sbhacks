/* Native drawing fixture; no game process or real network connection. */
#define SBPE_ANY_MAP_MAIN prior_loading_main
#include "test_any_map_loading.c"
#undef SBPE_ANY_MAP_MAIN
static void multibox_snapshot(const char *directory,const char *name,int width,int height,int ratio,int open,int enabled,int clients){
    memset(&mb,0,sizeof(mb));mb.fd=-1;mb.inited=1;mb.role=MB_LEADER;mb.instance=1;mb.enabled_override=enabled;
    mb.self=(struct MultiboxState){.instance=1,.leader=1,.valid=1,.hp=80,.maxhp=100,.capabilities=MB_CAP_CONTROL,.control_off=!enabled,.w=2560,.h=5120,.name="Hashem"};
    mb.npeers=clients-1;
    for(int i=0;i<mb.npeers;++i){mb.peers[i].s=mb.self;mb.peers[i].s.instance=10+i;mb.peers[i].s.leader=0;mb.peers[i].s.capabilities=MB_CAP_CONTROL|MB_CAP_RECONNECT;
        mb.peers[i].s.hp=100-i*8;mb.peers[i].s.x=i*5000;snprintf(mb.peers[i].s.name,sizeof(mb.peers[i].s.name),"steam-%d",i+1);mb.peers[i].has_addr=1;}
    probe_clients_height=mb_connection_height;probe_below_height=mb_below_height;physical_w=width;physical_h=height;render_pixel_ratio=ratio;probe_gui_visible=open;
    text_slot=0;gui_next_texture=0;memset(texts,0,sizeof(texts));
    if(directory){char path[4096];snprintf(path,sizeof(path),"%s/%s.svg",directory,name);preview=fopen(path,"w");assert(preview);
        fprintf(preview,"<svg xmlns='http://www.w3.org/2000/svg' width='%d' height='%d'><rect width='%d' height='%d' fill='#09233a'/>\n",width,height,width,height);}
    int w=width*ratio,h=height*ratio;canvas_w=&w;canvas_h=&h;
    loading_probe_overlay();multibox_connections_overlay();multibox_overlay();
    assert(w==width*ratio&&h==height*ratio);
    if(preview){fputs("</svg>\n",preview);fclose(preview);preview=NULL;}
    canvas_w=canvas_h=NULL;
}
int main(int argc,char **argv){
    logfile=tmpfile();assert(logfile);manual_context();probe_record_failed=0;loading_probe_installed=1;set_option("plugin_loading_probe","enabled","yes");
    create_text=gui_make_text;query_texture=gui_query;draw_texture=gui_texture;fill_rect=gui_rectangle;
    const char *out=argc>1?argv[1]:NULL;
    multibox_snapshot(out,"multibox-expanded",1280,800,1,1,1,3);
    multibox_snapshot(out,"multibox-collapsed-off",800,600,1,0,0,5);
    multibox_snapshot(out,"multibox-paginated",800,600,1,1,1,9);
    multibox_snapshot(out,"multibox-small",640,480,1,1,1,3);
    multibox_snapshot(out,"multibox-minimum",280,304,1,1,1,3);
    multibox_snapshot(out,"multibox-minimum-collapsed",280,304,1,0,1,3);
    /* Draw bounds and coordinate restoration must hold under Retina too. */
    multibox_snapshot(NULL,"retina-expanded",1280,800,2,1,1,3);
    multibox_snapshot(NULL,"retina-collapsed",800,600,2,0,0,9);
    fclose(logfile);logfile=NULL;
    puts("PASS: combined native Loading test + client health/reconnect rows + multibox controls; expanded/collapsed/Off, pagination, small windows, Retina bounds and canvas restoration.");return 0;
}

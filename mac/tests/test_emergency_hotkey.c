#define SBPE_EMERGENCY_MAIN previous_emergency_fixture_main
#include "test_reconnect_lab.c"
static unsigned hotkey_forwards;
static int hotkey_lookup(const char *name){
    if(!strcmp(name,"F4"))return 61;if(!strcmp(name,"F11"))return 68;
    if(!strcmp(name,"J"))return 13;if(!strcmp(name,"E"))return 8;return manual_lookup(name);
}
static int hotkey_from_key(int key){
    if(key&0x40000000)return key&0x3fffffff;
    return key=='j'?13:key=='e'?8:0;
}
static int hotkey_forward(struct Stage *stage,int down,int key){(void)stage;(void)down;(void)key;++hotkey_forwards;return 1;}
static void hotkey_context(struct Stage *stage){
    lab_context();nbindings=0;hotkey_forwards=0;memset(stage,0,sizeof(*stage));
    memset(event_keys,0,sizeof(event_keys));event_input_enabled=1;key_from_name=hotkey_lookup;scancode_from_key=hotkey_from_key;original_stage_keyboard=hotkey_forward;
    set_option("sbpe_controls","disconnect_hold_primary","F4");set_option("sbpe_controls","disconnect_hold_secondary","None");set_option("sbpe_controls","disconnect_hold_tertiary","None");controls_load();
}
int main(int argc,char **argv){
    previous_emergency_fixture_main(argc,argv);struct Stage stage={0},*stage_pointer=&stage;stage_ptr=&stage_pointer;
    hotkey_context(&stage);dc_lab.visible=0;
    stage_keyboard(&stage,1,0x4000003d);assert(dc_lab.state==DC_QUEUED&&dc_lab.trial==1&&!lab_losses&&!hotkey_forwards);
    stage_keyboard(&stage,1,0x4000003d);assert(dc_lab.trial==1&&!hotkey_forwards);
    stage_keyboard(&stage,0,0x4000003d);assert(!dc_lab.owned[61]&&!hotkey_forwards);
    assert(network_do_io(&connection)==0&&lab_losses==1);
    hotkey_context(&stage);stage.textInputTarget=(void*)1;stage_keyboard(&stage,1,0x4000003d);
    assert(dc_lab.state==DC_IDLE&&!network_loading_reconnect.connection);stage.textInputTarget=NULL;keyboard();assert(dc_lab.state==DC_IDLE);stage_keyboard(&stage,0,0x4000003d);
    stage_keyboard(&stage,1,0x4000003d);assert(dc_lab.state==DC_QUEUED);stage_keyboard(&stage,0,0x4000003d);
    hotkey_context(&stage);active_controls=(void*)1;stage_keyboard(&stage,1,0x4000003d);assert(dc_lab.state==DC_IDLE);active_controls=NULL;stage_keyboard(&stage,0,0x4000003d);
    hotkey_context(&stage);paused=1;stage_keyboard(&stage,1,0x4000003d);assert(dc_lab.state==DC_IDLE);paused=0;keyboard();assert(dc_lab.state==DC_IDLE);stage_keyboard(&stage,0,0x4000003d);
    hotkey_context(&stage);set_option(DC_LAB_SECTION,"enabled","no");stage_keyboard(&stage,1,0x4000003d);assert(dc_lab.state==DC_IDLE);stage_keyboard(&stage,0,0x4000003d);
    hotkey_context(&stage);set_option("sbpe_controls","disconnect_hold_primary","J");controls_load();
    stage_keyboard(&stage,1,0x4000003d);assert(dc_lab.state==DC_IDLE);stage_keyboard(&stage,0,0x4000003d);stage_keyboard(&stage,1,'j');assert(dc_lab.state==DC_QUEUED);stage_keyboard(&stage,0,'j');
    hotkey_context(&stage);set_option("sbpe_controls","disconnect_hold_primary","E");controls_load();
    stage_keyboard(&stage,1,'e');assert(dc_lab.state==DC_QUEUED&&dc_lab.trial==1&&!hotkey_forwards);
    stage_keyboard(&stage,1,'e');assert(dc_lab.trial==1&&!hotkey_forwards);
    stage_keyboard(&stage,0,'e');assert(!dc_lab.owned[8]&&!hotkey_forwards);
    hotkey_context(&stage);uint8_t keys[512]={0};keys[61]=1;nbindings=1;bindings[0].scancode=61;
    reconnect_lab_keys(keys,512,1);assert(dc_lab.state==DC_IDLE&&!network_loading_reconnect.connection);assert(!reconnect_lab_consumes(&stage,1,0x4000003d,0));
    nbindings=0;keys[61]=0;reconnect_lab_keys(keys,512,1);keys[61]=1;reconnect_lab_keys(keys,512,0);reconnect_lab_keys(keys,512,1);assert(dc_lab.state==DC_IDLE);
    hotkey_context(&stage);set_option("sbpe_controls","disconnect_hold_primary","F10");controls_load();memset(keys,0,sizeof(keys));keys[67]=1;reconnect_lab_keys(keys,512,1);assert(dc_lab.state==DC_IDLE);
    hotkey_context(&stage);stage_keyboard(&stage,1,0x4000003d);set_option(DC_LAB_SECTION,"enabled","no");stage_keyboard(&stage,0,0x4000003d);assert(!dc_lab.owned[61]&&!hotkey_forwards);
    if(argc>1){
        hotkey_context(&stage);physical_w=800;physical_h=600;int width=2400,height=1800;canvas_w=&width;canvas_h=&height;
        text_slot=0;gui_next_texture=0;memset(texts,0,sizeof(texts));char path[4096];snprintf(path,sizeof(path),"%s/emergency-panel.svg",argv[1]);
        preview=fopen(path,"w");assert(preview);fputs("<svg xmlns='http://www.w3.org/2000/svg' width='800' height='600'><rect width='800' height='600' fill='#09233a'/>\n",preview);
        reconnect_lab_overlay();fputs("</svg>\n",preview);fclose(preview);preview=NULL;assert(width==2400&&height==1800);
    }
    probe_record_close();puts("PASS: Emergency hold F4 on native key events with panel hidden; exact-once edges and paired releases; chat/Controls/pause/disable/background guards, remapping, conflict protection and reserved loading keys.");return 0;
}

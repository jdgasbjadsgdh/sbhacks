#include <assert.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define LOG(...) ((void)0)
#define SBPE_NETWORK_GUARD_TEST
#include "../src/network_guard.h"
struct Connection {
    uint8_t a[0x28];int state;uint8_t b[0x54-0x2c];int socket;
    uint8_t c[0x70-0x58];uint8_t type,pad[3];uint32_t length;
    uint8_t d[0xa0-0x78];void *cipher;uint8_t e[8];
    void *buffer;uint64_t allocation,received;
};
_Static_assert(offsetof(struct Connection,received)==0xc0,"Native ABI");
static struct Connection c;static int peer,new_peer,new_socket;
static unsigned calls,mode;static int inside,fail_alloc;
static void *allocate(size_t n){return fail_alloc?NULL:malloc(n);}
static void frame(int fd,int value){uint8_t bytes[]={37,0,0,0,2,1,(uint8_t)value};assert(write(fd,bytes,sizeof(bytes))==(ssize_t)sizeof(bytes));}
static void received(void *handlers,int type,const void *data,int length){
    assert(!inside&&handlers==(uint8_t*)&c+0x78&&type==37&&length==2);
    const uint8_t *p=data;assert(p[0]==1);++calls;assert(p[1]==calls);
    if(mode==1&&calls==1){inside=1;assert(network_receive(&c)==1&&calls==1);inside=0;}
    if(mode==2&&calls==1){c.socket=new_socket;c.type=0;c.length=0;c.received=0;}
    if(mode==3&&calls==1)c.state=2;
    if(mode==4&&calls==1)network_reconnect_pending=&c;
    if(mode==5&&calls==1)network_receive_reset(&c);
}
static void initialize(void){
    int sockets[2];assert(!socketpair(AF_UNIX,SOCK_STREAM,0,sockets));
    c=(struct Connection){.state=3,.socket=sockets[1]};peer=sockets[0];calls=mode=0;inside=fail_alloc=0;
    memset(network_receive_states,0,sizeof(network_receive_states));network_reconnect_pending=NULL;
    network_receive_available=network_receive_fionread;network_receive_dispatch=received;
    network_receive_alloc=allocate;network_receive_free=free;network_receive_recv=recv;network_receive_installed=1;
}
static void cleanup(void){close(peer);close(c.socket);free(c.buffer);network_receive_reset(&c);}
static void test_dispatch_lifecycle(void){
    initialize();mode=1;frame(peer,1);frame(peer,2);assert(network_receive(&c)==1&&calls==2&&!c.type);cleanup();
    initialize();mode=2;int sockets[2];assert(!socketpair(AF_UNIX,SOCK_STREAM,0,sockets));new_peer=sockets[0];new_socket=sockets[1];int old=c.socket;
    frame(peer,1);frame(peer,99);frame(new_peer,2);
    assert(network_receive(&c)==1&&calls==1&&!c.type); /* old budget cannot consume new stream */
    assert(network_receive(&c)==1&&calls==2);close(old);close(new_peer);cleanup();
    initialize();mode=3;frame(peer,1);frame(peer,2);assert(network_receive(&c)==1&&calls==1&&c.state==2);
    c.state=3;c.type=0;assert(network_receive(&c)==1&&calls==2);cleanup();
    initialize();mode=4;frame(peer,1);frame(peer,2);assert(network_receive(&c)==0&&calls==1&&!network_reconnect_pending);cleanup();
    initialize();mode=5;frame(peer,1);frame(peer,2);assert(network_receive(&c)==1&&calls==1);
    c.type=0;assert(network_receive(&c)==1&&calls==2);cleanup();
}
static void test_eof_bounds_and_cache(void){
    initialize();uint8_t head[]={37,0,0,0,2};
    assert(write(peer,head,2)==2);assert(network_receive(&c)==1&&!calls&&!c.type);
    close(peer);peer=-1;assert(network_receive(&c)==0&&!calls);cleanup();
    initialize();assert(write(peer,head,5)==5);uint8_t first=1;assert(write(peer,&first,1)==1);
    assert(network_receive(&c)==1&&!calls&&c.type==37&&c.received==1);
    close(peer);peer=-1;assert(network_receive(&c)==0&&!calls);cleanup();
    initialize();uint8_t huge[]={37,1,0,0,1};assert(write(peer,huge,5)==5);
    assert(network_receive(&c)==0&&!calls&&!c.buffer);cleanup();
    initialize();fail_alloc=1;assert(write(peer,head,5)==5);assert(network_receive(&c)==0&&!calls&&!c.buffer);cleanup();
    initialize();assert(write(peer,head,2)==2);assert(network_receive(&c)==1&&!calls);
    /* A new native connection reuses the object; discard its partial header. */
    network_receive_reset(&c);close(peer);close(c.socket);int sockets[2];assert(!socketpair(AF_UNIX,SOCK_STREAM,0,sockets));peer=sockets[0];c.socket=sockets[1];
    frame(peer,1);assert(network_receive(&c)==1&&calls==1);cleanup();
}
static void test_independent_headers(void){
    initialize();struct Connection other={0};int sockets[2];assert(!socketpair(AF_UNIX,SOCK_STREAM,0,sockets));other.state=3;other.socket=sockets[1];
    uint8_t a[]={37,0},b[]={37,0,0};assert(write(peer,a,2)==2&&write(sockets[0],b,3)==3);
    assert(network_receive(&c)==1&&network_receive(&other)==1);
    struct NetworkReceiveState *left=network_receive_state(&c,c.socket),*right=network_receive_state(&other,other.socket);
    assert(left!=right&&left->have==2&&right->have==3);network_receive_reset(&other);close(sockets[0]);close(sockets[1]);cleanup();
}
static void test_cipher_diagnostics(void){
    initialize();uint8_t cipher[258]={0},replacement[258]={0};
    for(unsigned i=0;i<256;++i)cipher[i+2]=replacement[i+2]=(uint8_t)i;
    c.cipher=cipher;assert(network_receive_cipher_permutation(cipher));
    struct NetworkReceiveState *s=network_receive_state(&c,c.socket);
    network_receive_check_cipher(s,&c,"baseline");assert(s->cipher_checks==1&&!s->cipher_changes);
    network_receive_check_cipher(s,&c,"unchanged");assert(s->cipher_checks==2&&!s->cipher_changes);
    cipher[0]++;network_receive_check_cipher(s,&c,"unexpected index mutation");assert(s->cipher_changes==1);
    uint8_t swap=cipher[2];cipher[2]=cipher[3];cipher[3]=swap;
    assert(network_receive_cipher_permutation(cipher));
    network_receive_check_cipher(s,&c,"unexpected valid permutation mutation");assert(s->cipher_changes==2);
    cipher[2]=cipher[3];assert(!network_receive_cipher_permutation(cipher));
    network_receive_check_cipher(s,&c,"damaged permutation");assert(s->cipher_changes==3);
    c.cipher=replacement;network_receive_check_cipher(s,&c,"native context replacement");assert(s->cipher_changes==3);
    network_receive_reset(&c);assert(!s->cipher_seen&&!s->cipher);c.cipher=NULL;cleanup();
}
int main(void){test_dispatch_lifecycle();test_eof_bounds_and_cache();test_independent_headers();test_cipher_diagnostics();
    puts("PASS: streaming receiver on real sockets: reentrant dispatch, socket/state/generation transitions, deferred rejection, EOF in partial header/payload, length/allocation bounds, reused connection cache and independent connections.");}

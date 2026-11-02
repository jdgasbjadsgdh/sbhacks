#include <assert.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#define LOG(...) ((void)0)
#define SBPE_NETWORK_GUARD_TEST
#include "../src/network_guard.h"
struct Connection {
    unsigned result,native_calls,failures;
    uint8_t gap[0x28-12];int state;uint8_t gap2[0x54-0x2c];int socket;
    uint8_t gap3[0x70-0x58];uint8_t type;uint8_t pad[3];uint32_t length;
    uint8_t gap4[0xc0-0x78];uint64_t received;
};
_Static_assert(offsetof(struct Connection,state)==0x28,"state");
_Static_assert(offsetof(struct Connection,socket)==0x54,"socket");
_Static_assert(offsetof(struct Connection,type)==0x70,"type");
_Static_assert(offsetof(struct Connection,length)==0x74,"length");
_Static_assert(offsetof(struct Connection,received)==0xc0,"received bytes");
static void test_deadline(void){
    struct Connection c={.state=3,.socket=9,.type=37,.length=8881378,.received=100};
    memset(&network_partial,0,sizeof(network_partial));network_partial_timeout_ms=5000;network_partial_lifetime_ms=0;
    assert(!network_partial_stalled(&c,0)&&!network_partial_stalled(&c,4999));
    assert(network_partial_stalled(&c,5000));
    c.received+=1;assert(!network_partial_stalled(&c,5001)&&!network_partial_stalled(&c,10000));
    assert(network_partial_stalled(&c,10001));
    ++network_header_sequence;assert(!network_partial_stalled(&c,20000)); /* new frame, identical size/type */
    c.socket=10;assert(!network_partial_stalled(&c,30000));
    struct Connection other=c;assert(!network_partial_stalled(&other,40000));
    assert(!network_partial_stalled(&other,1)); /* monotonic reset */
    other.received=other.length;assert(!network_partial_stalled(&other,99999)&&!network_partial.connection);
    other.received=0;other.type=0;assert(!network_partial_stalled(&other,100000));
    other.type=37;other.state=2;assert(!network_partial_stalled(&other,100000));
    other.state=3;other.socket=-1;assert(!network_partial_stalled(&other,100000));
    other.socket=1;network_partial_timeout_ms=0;assert(!network_partial_stalled(&other,100001)&&!network_partial_stalled(&other,UINT64_MAX));
    network_partial_timeout_ms=5000;
}
static void test_trickling_deadline(void){
    struct Connection c={.state=3,.socket=9,.type=37,.length=9591167,.received=1};
    memset(&network_partial,0,sizeof(network_partial));network_partial_timeout_ms=5000;network_partial_lifetime_ms=10000;
    assert(!network_partial_stalled(&c,0));
    for(uint64_t now=100;now<10000;now+=100){c.received+=1024;assert(!network_partial_stalled(&c,now));}
    c.received++;assert(network_partial_stalled(&c,10000)&&network_partial.progress_ms==10000&&network_partial.started_ms==0);
    ++network_header_sequence;assert(!network_partial_stalled(&c,10001)&&network_partial.started_ms==10001);
    c.received=c.length;assert(!network_partial_stalled(&c,30000)&&!network_partial.connection); /* completion wins */
    c.received=1;assert(!network_partial_stalled(&c,30001));c.socket++;assert(!network_partial_stalled(&c,40002));
    assert(!network_partial_stalled(&c,1)); /* backwards clock resets both timers */
    network_partial_lifetime_ms=0;
}
static unsigned char native(void *p){struct Connection *c=p;++c->native_calls;return (unsigned char)c->result;}
static unsigned char failure(void *p){struct Connection *c=p;assert(c->native_calls);++c->failures;c->state=4;return 0;}
static uint64_t recovery_time;
static uint64_t recovery_now(void){return recovery_time;}
static void test_entry(void){
    struct Connection c={.result=1,.state=3,.socket=9,.type=37,.length=1000,.received=1};
    network_continue_io=native;network_failure_io=failure;
    unsigned char (*entry)(void*)=network_do_io;
#ifdef __x86_64__
    /* Same native frame/prologue and R12=this setup as ServerConnection::doIO.
       The two bodies stand in for a returned I/O pump and its error callback. */
    const uint8_t normal[]={0x49,0x89,0xfc,0x41,0xff,0x44,0x24,4,0x41,0x8b,4,0x24,
        0x48,0x83,0xc4,0x60,0x5b,0x41,0x5c,0x41,0x5e,0x41,0x5f,0x5d,0xc3};
    const uint8_t fail[]={0x41,0xff,0x44,0x24,8,0x41,0xc7,0x44,0x24,0x28,4,0,0,0,0x31,0xc0,
        0x48,0x83,0xc4,0x60,0x5b,0x41,0x5c,0x41,0x5e,0x41,0x5f,0x5d,0xc3};
    size_t page=(size_t)sysconf(_SC_PAGESIZE);uint8_t *code=mmap(NULL,page,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANON,-1,0);assert(code!=MAP_FAILED);
    memcpy(code,network_io_original,15);memcpy(code+15,normal,sizeof(normal));memcpy(code+128,fail,sizeof(fail));assert(!mprotect(code,page,PROT_READ|PROT_EXEC));
    assert(network_progress_apply(code,(uintptr_t)code+15,(uintptr_t)code+128));entry=(void*)code;
    uint8_t mismatch[15]={0};assert(!network_progress_apply(mismatch,0,0));
#endif
    memset(&network_partial,0,sizeof(network_partial));assert(entry(&c)==1&&c.native_calls==1&&!c.failures);
    network_partial.progress_ms=network_progress_now()-6000;
    assert(entry(&c)==0&&c.native_calls==2&&c.failures==1&&c.state==4&&!network_partial.connection);
    c.state=3;c.received=20;assert(entry(&c)==1&&c.native_calls==3&&c.failures==1);
    network_partial.progress_ms=network_progress_now()-6000;c.received=21;
    assert(entry(&c)==1&&c.native_calls==4&&c.failures==1); /* arriving bytes win over deadline */
    c.result=0;assert(entry(&c)==0&&c.native_calls==5&&c.failures==1&&!network_partial.connection);
    /* A rejected update followed by silence still reaches one native recovery
       after I/O returns; it does not need another bad packet to trip it. */
    c.result=1;c.state=3;c.type=0;network_delta_clock=recovery_now;recovery_time=10000;
    memset(&network_delta_errors,0,sizeof(network_delta_errors));network_delta_errors.connection=&c;
    network_delta_errors.started_ms=10000;network_delta_errors.rejected=1;
    recovery_time=14999;assert(entry(&c)==1&&c.failures==1&&network_delta_errors.rejected);
    recovery_time=15000;assert(entry(&c)==0&&c.failures==2&&c.state==4&&!network_delta_errors.rejected&&!network_reconnect_pending);
    assert(!network_delta_stalled(&c,99999));network_delta_clock=network_progress_now;
#ifdef __x86_64__
    munmap(code,page);
#endif
}
int main(void){test_deadline();test_trickling_deadline();test_entry();puts("PASS: incomplete-frame deadlines and bounded rejected-update silence recovery; new-frame/socket/state/clock resets, completion wins; native I/O runs first, recovery after return; x86_64 trampoline preserves native frame/R12 and error path.");}

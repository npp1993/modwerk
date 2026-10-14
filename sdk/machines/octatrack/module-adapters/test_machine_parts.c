/* SPDX-License-Identifier: GPL-3.0-or-later; synthetic Part records only. */
#include "machine_parts.h"
#include <assert.h>
#include <string.h>
#include <stdio.h>
#define BANK 0x400e21e0u
#define STRIDE 6322u
static uint8_t regions[4][4 * STRIDE];
static uint8_t settings[128][0x448];
static unsigned reads;
static int unreadable;
static uint32_t bank;
static uint32_t base(unsigned r) { return r == 0 ? bank + 0x8ed80u : r == 1 ? bank + 0x9504au : r == 2 ? 0x100a4eceu : 0x100ab196u; }
static int read_part(void *unused, uint32_t address, uint8_t *out, unsigned n)
{
    (void)unused; ++reads;
    if (unreadable == 1) return 0;
    for (unsigned r=0;r<4;++r) if (address >= base(r) && address-base(r) <= sizeof regions[r] && n <= sizeof regions[r]-(address-base(r))) {
        memcpy(out,regions[r]+address-base(r),n);return 1;
    }
    if (address >= 0x100b14f0u && address-0x100b14f0u < sizeof settings &&
        n <= sizeof settings-(address-0x100b14f0u)) {
        if (unreadable == 2) return 0;
        memcpy(out,(const uint8_t *)settings+address-0x100b14f0u,n);return 1;
    }
    assert(0);return 0;
}
static void fm_layout(void)
{
    const char *paths[]={"SYNTH.wav","folder/FMSYNTH bass.wav","SYNTH","folder/SYNTH suffix",
                        "folder/FMSYNTH","synth.wav","xxFMSYNTH.wav","FMSYNTH/ordinary.wav","","ordinary.wav"};
    const uint8_t values[]={1,2,3,127,255};
    for (unsigned alias=0;alias<2;++alias) for (unsigned region=0;region<4;++region)
        for (unsigned part=0;part<4;++part) for (unsigned track=0;track<8;++track) {
            bank=BANK+alias*0x08000000u;
            memset(regions,0,sizeof regions);memset(settings,0,sizeof settings);
            uint8_t *p=regions[region]+part*STRIDE;
            for (unsigned type=0;type<=4;++type) {
                p[0x22+track]=(uint8_t)type;
                for (unsigned value=0;value<sizeof values;++value) {
                    p[0x2fd+30*track]=values[value];
                    assert(machine_part_lifetime(read_part,0,bank,4)==MACHINE_PART_FM_LEG);
                    assert(machine_part_lifetime(read_part,0,bank,3)==MACHINE_PART_CLEAR);
                }
            }
            p[0x2fd+30*track]=0;
            p[0x22+track]=1;
            for (unsigned slot=0;slot<=127;slot+=127) {
                p[0x2cb+5*track]=(uint8_t)slot;
                for (unsigned path=0;path<sizeof paths/sizeof *paths;++path) {
                    memset(settings,0,sizeof settings);strcpy((char *)settings[slot],paths[path]);
                    assert(machine_part_lifetime(read_part,0,bank,4)==
                           (path<5?MACHINE_PART_FM_MARKER:MACHINE_PART_CLEAR));
                    p[0x22+track]=0; /* STATIC has no legacy marker fallback. */
                    assert(machine_part_lifetime(read_part,0,bank,4)==MACHINE_PART_CLEAR);
                    p[0x22+track]=1;
                }
            }
            p[0x2cb+5*track]=128;
            unreadable=2;assert(machine_part_lifetime(read_part,0,bank,4)==MACHINE_PART_CLEAR);
            p[0x2cb+5*track]=255;
            assert(machine_part_lifetime(read_part,0,bank,4)==MACHINE_PART_CLEAR);
            p[0x2cb+5*track]=127;
            assert(machine_part_lifetime(read_part,0,bank,4)==MACHINE_PART_UNKNOWN);
            unreadable=0;
            memset(settings[127],'x',256);
            assert(machine_part_lifetime(read_part,0,bank,4)==MACHINE_PART_UNKNOWN);
            settings[127][249]='/';memcpy(settings[127]+250,"SYNTH",5);settings[127][255]=0;
            assert(machine_part_lifetime(read_part,0,bank,4)==MACHINE_PART_FM_MARKER);
            memset(settings,0,sizeof settings);p[0x22+track]=255;
            assert(machine_part_lifetime(read_part,0,bank,4)==MACHINE_PART_UNKNOWN);
        }
    memset(regions,0,sizeof regions);memset(settings,0,sizeof settings);
}
int main(void)
{
    const uint8_t signatures[4][3]={{'P','L',1},{'S','2',1},{'S','2',2},{'F','M',1}};
    const unsigned bits[4]={1,2,2,4};
    for (unsigned alias=0;alias<2;++alias) for (unsigned region=0;region<4;++region) for(unsigned part=0;part<4;++part) for(unsigned track=0;track<8;++track)
        for(unsigned m=0;m<4;++m) {
            bank = BANK + alias * 0x08000000u;
            memset(regions,0,sizeof regions);
            memcpy(regions[region]+part*STRIDE+60+track*30,signatures[m],3);
            assert(machine_part_lifetime(read_part,0,bank,bits[m])==1);
            assert(machine_part_lifetime(read_part,0,bank,7u & ~bits[m])==0);
            regions[region][part*STRIDE+0x22+track]=2;
            assert(machine_part_lifetime(read_part,0,bank,bits[m])==0);
        }
    fm_layout();
    memset(regions,0,sizeof regions);
    for (unsigned alias=0;alias<2;++alias) {
        bank=0x40000000u+alias*0x08000000u;
        assert(machine_part_lifetime(read_part,0,bank,7)==0);
        bank=0x47f00000u-(0x9504au+4u*STRIDE)+alias*0x08000000u;
        assert(machine_part_lifetime(read_part,0,bank,7)==0);
        reads=0;
        assert(machine_part_lifetime(read_part,0,bank+2,1)==2 && !reads);
    }
    reads=0;assert(machine_part_lifetime(read_part,0,0,0)==0 && !reads);
    assert(machine_part_lifetime(read_part,0,0,1)==2 && !reads);
    assert(machine_part_lifetime(read_part,0,0xffffffffu,1)==2 && !reads);
    assert(machine_part_lifetime(read_part,0,0x47efffffu,1)==2 && !reads);
    assert(machine_part_lifetime(read_part,0,0x4fefffffu,1)==2 && !reads);
    assert(machine_part_lifetime(read_part,0,0x4ff00000u,1)==2 && !reads);
    assert(machine_part_lifetime(read_part,0,BANK+1,1)==2 && !reads);
    assert(machine_part_lifetime(read_part,0,BANK+0x08000001u,1)==2 && !reads);
    assert(machine_part_lifetime(0,0,BANK,1)==2 && !reads);
    assert(machine_part_lifetime(read_part,0,BANK,8)==2 && !reads);
    unreadable=1;assert(machine_part_lifetime(read_part,0,BANK,1)==2);
    assert(machine_part_lifetime(read_part,0,BANK+0x08000000u,1)==2);
    puts("Machine Parts: cached/uncached banks preserve RAM read aliases and fixed SRAM mirrors; all four working/saved regions, every Part/track/signature, explicit FM LEG/marker retention, conservative stock TRIG values, unknown paths/bounds and stock fallback passed (synthetic data only).");
    return 0;
}

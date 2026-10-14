// SPDX-License-Identifier: GPL-3.0-or-later
// Private actual ColdFire controller execution. No DSP, transport or boot proof.
#include <array>
#include <cassert>
#include <cstdio>
#include <fstream>
#include <iterator>
#include <map>
#include <string>
#include <vector>
#include "machine.h"
#include "mc68k/Musashi/m68k.h"
#include "mc68k/cpuState.h"

static constexpr uint32_t stack=0x46c7f920,stop=0x47300000,bank=0x400e21e0;
static std::vector<uint8_t> load(const char *path) {
    std::ifstream f(path,std::ios::binary); assert(f.good()); return {(std::istreambuf_iterator<char>(f)),{}};
}
int main(int argc,char **argv) {
    assert(argc==6 || argc==7);
    const bool guarded=argc==7 && std::string(argv[6])=="guarded";
    const uint32_t origin=std::stoul(argv[4],nullptr,0);
    const std::string module=argv[5]; assert(module=="sidechain-compressor" || module=="output-matrix");
    auto image=load(argv[2]); ot::Machine m(load(argv[1]));
    for(unsigned i=0;i<image.size();++i)m.write8(origin+i,image[i]);
    std::map<std::string,uint32_t> symbols; std::ifstream f(argv[3]); std::string name; uint32_t offset;
    while(f>>name>>offset)symbols[name]=origin+offset;
    m.mapRegion(0x10000000,0x000c0000); m.mapRegion(0x100c0000,0x00040000);
    m.write32(0x46c82456,bank);
    auto read=[&](uint32_t at,unsigned n) { std::vector<uint8_t>b(n);for(unsigned i=0;i<n;++i)b[i]=m.read8(at+i);return b; };
    auto write=[&](uint32_t at,const std::vector<uint8_t>&b) { for(unsigned i=0;i<b.size();++i)m.write8(at+i,b[i]); };
    auto cpu=m.getCpuState(); unsigned calls=0,instructions=0,maxHeld=0,maxMode=0;
    unsigned gateCase=0,begins=0,ends=0,heldInstructions=0,redraws=0,modeLeases=0,frameLeases=1;bool held=false,modeEntry=false,handler=false;
    std::string modeLease="matrix_leave";
    // Executed module instructions per call in the cases a frame meets most (the fixture's Begin/End not counted).
    std::map<std::string,unsigned> cost;
    std::vector<std::array<uint32_t,3>> notifications;
    uint32_t lease=0;std::array<uint32_t,15> endOutputs{};uint16_t endCcr=0;
    auto get=[&](unsigned r) {return m68k_get_reg(cpu,m68k_register_t(M68K_REG_D0+r));};
    auto enter=[&](const char *entry) {
        modeEntry=std::string(entry)=="set_mode";handler=std::string(entry)=="sc_mute_keep";
        for(unsigned r=0;r<15;++r)m68k_set_reg(cpu,m68k_register_t(M68K_REG_D0+r),0x47070000+4*r);
        m68k_set_reg(cpu,M68K_REG_SP,stack);m.write32(stack,stop);
        m68k_set_reg(cpu,M68K_REG_SR,0x2013);m68k_set_reg(cpu,M68K_REG_PC,symbols.at(entry));
    };
    auto run=[&]() {
        const auto unmapped=m.unmappedCount(); unsigned budget=200000;const unsigned started=instructions;
        while(m.pc()!=stop && budget--){
            const uint32_t pc=m.pc(),sp=m68k_get_reg(cpu,M68K_REG_SP);
            if(guarded && pc==0x47410000) {
                ++begins;assert(!held);
                assert(m.read32(sp+4)==symbols.at(module=="sidechain-compressor"?"sc_norm":modeEntry?modeLease:"page_levels"));
                assert(m.read32(sp+8)==(module=="sidechain-compressor"?1u:2u));
                lease=m.read32(sp+12);assert((lease&3)==0 && lease==stack-(modeEntry?112u:104u));
                held=gateCase==1 || gateCase==2;heldInstructions=0;
                if(held){for(unsigned i=0;i<8;++i)m.write32(lease+4*i,0xa5a50000+i);m68k_set_reg(cpu,M68K_REG_SR,0x241f);}
                for(unsigned r:{1u,8u,9u})m68k_set_reg(cpu,m68k_register_t(M68K_REG_D0+r),0xdead0000+r);
                m68k_set_reg(cpu,M68K_REG_D0,held?1:(gateCase==4?2:0));
                m68k_set_reg(cpu,M68K_REG_PC,m.read32(sp));m68k_set_reg(cpu,M68K_REG_SP,sp+4);continue;
            }
            if(guarded && pc==0x47410100) {
                ++ends;assert(held && m.read32(sp+4)==lease);
                for(unsigned r=0;r<15;++r)endOutputs[r]=m.read32(lease+32+4*r);
                endCcr=m.read16(lease+92)&31;
                if(gateCase==2)m.write32(lease,0); // corrupt caller storage cannot own IRQ restoration
                held=false;maxHeld=std::max(maxHeld,heldInstructions);
                m68k_set_reg(cpu,M68K_REG_SR,0x201f); // independent fixture backend record
                for(unsigned r:{1u,8u,9u})m68k_set_reg(cpu,m68k_register_t(M68K_REG_D0+r),0xbeef0000+r);
                m68k_set_reg(cpu,M68K_REG_D0,gateCase==2?0:1);
                m68k_set_reg(cpu,M68K_REG_PC,m.read32(sp));m68k_set_reg(cpu,M68K_REG_SP,sp+4);continue;
            }
            if(pc==0x40033e3c || pc==0x4004d948) {
                assert(!held);
                if(pc==0x40033e3c)notifications.push_back({m.read32(sp+4),m.read32(sp+8),m.read32(sp+12)});
                else{assert(m.read32(sp+4)==0xffffffff);++redraws;}
                m68k_set_reg(cpu,M68K_REG_PC,m.read32(sp));m68k_set_reg(cpu,M68K_REG_SP,sp+4);continue;
            }
            if(held){assert((m68k_get_reg(cpu,M68K_REG_SR)&0x700)==0x400);++heldInstructions;}
            assert(m.step());++instructions;
        }
        assert(m.pc()==stop && m.unmappedCount()==unmapped);
        assert(m68k_get_reg(cpu,M68K_REG_SP)==stack+4 && !held);
        assert((m68k_get_reg(cpu,M68K_REG_SR)&0x700)==0);
        // A frame hook leases only when its body would write (its read-only precheck); a mode change when it converts.
        const unsigned leases=handler?0u:modeEntry?modeLeases:frameLeases;
        if(guarded){assert(begins==leases && ends==unsigned(leases && (gateCase==1 || gateCase==2)));
            if(ends && !modeEntry){for(unsigned r=0;r<15;++r)assert(get(r)==endOutputs[r]);assert((m68k_get_reg(cpu,M68K_REG_SR)&31)==endCcr);}}
        if(modeEntry)maxMode=std::max(maxMode,instructions-started);
        ++calls;
    };
    if(module=="sidechain-compressor") {
        constexpr unsigned stride=6322,lane=72;
        const std::array<unsigned,6> keys={0,1,8,9,127,255};
        for(unsigned part=0;part<4;++part)for(unsigned track=0;track<8;++track)
        for(unsigned slot=0;slot<2;++slot)for(unsigned ids=0;ids<4;++ids)for(unsigned key:keys)
        for(unsigned gate=0;gate<(guarded?5u:1u);++gate) {
            gateCase=gate;begins=ends=0;
            const uint32_t working=bank + 0x8ed80 + part*stride,saved=bank + 0x9504a + part*stride,mirror=0x100a4ece + part*stride;
            std::vector<uint8_t> store(stride,0x55),live(8*lane,0x66),guard(stride,0x77);
            for(unsigned t=0;t<8;++t){store[t]=store[8+t]=0;m.write8(0x80000ec4+t,0);m.write8(0x80000ecc+t,0);}
            store[8*slot+track]=(ids&1)?0x18:0x11;
            m.write8(0x80000ec4+8*slot+track,(ids&2)?0x18:0x11);
            const unsigned s=0x2f2+30*track+12+6*slot+2,l=lane*track+0x32+6*slot+2;
            store[s]=uint8_t(key);live[l]=uint8_t((key+7)%256);
            auto expectedStore=store,expectedLive=live;
            auto normalize=[](std::vector<uint8_t>&bytes,unsigned at) {if(bytes[at]>8){bytes[at]=0;bytes[at+1]=64;bytes[at+2]=64;bytes[at+3]=0;}};
            if(!guarded || gate==1 || gate==2){if(ids&1)normalize(expectedStore,s);if(ids&2)normalize(expectedLive,l);}
            frameLeases=((ids&1) && key>8) || ((ids&2) && (key+7)%256>8); // a KEY above 8 to reset
            write(working,store);write(saved,guard);write(mirror,guard);write(0x80000810,live);m.write8(0x80000003,uint8_t(part));
            enter("sc_norm");const unsigned before=instructions;run();
            if(part==0 && track==0 && slot==0 && gate==(guarded?1u:0u) && (key==1 || key==9) && (ids==0 || ids==3))
                cost[ids==0?"no COMPRESSOR":key==1?"COMPRESSOR, KEY 1":"COMPRESSOR, KEY 9 (normalized)"]=instructions-before;
            assert(read(working,stride)==expectedStore && read(0x80000810,8*lane)==expectedLive);
            assert(read(saved,stride)==guard && read(mirror,stride)==guard);
            for(unsigned r=0;r<15;++r)assert(get(r)==(r==11?0x80000a50u:0x47070000+4*r));
        }
        if(guarded) { // ev_mute_keep's handler: KEY tracks of every COMPRESSOR, bits 0..7 only
            for(unsigned seed=0;seed<512;++seed) {
                unsigned expected=0;
                for(unsigned t=0;t<8;++t) {
                    const uint32_t rec=0x80000110+64*t;
                    const unsigned a=(seed*7+t*13)%11,b=(seed*5+t*3)%13;
                    const uint8_t id1=(seed+t)%3?0x18:0x11,id2=(seed>>1)%2?0x18:0x05;
                    const uint8_t k1=uint8_t(a==10?127:a),k2=uint8_t(b>9?255:b);
                    m.write8(rec+55,id1);m.write8(rec+57,id2);m.write8(rec+38,k1);m.write8(rec+50,k2);
                    if(id1==0x18 && k1>=1 && k1<=8)expected|=1u<<(k1-1);
                    if(id2==0x18 && k2>=1 && k2<=8)expected|=1u<<(k2-1);
                }
                gateCase=0;begins=ends=0;enter("sc_mute_keep");run();
                assert(get(0)==expected);
                for(unsigned r:{2u,3u,4u,5u,6u,7u,10u,11u,12u,13u,14u})assert(get(r)==0x47070000+4*r);
            }
        }
        assert(read(origin,unsigned(image.size()))==image);
    } else {
        constexpr uint32_t page=0x47090000;
        for(unsigned mode=0;mode<3;++mode)for(unsigned base=0;base<16;++base)for(unsigned phones:{0u,64u,127u,255u})
        for(unsigned clear=0;clear<2;++clear)for(unsigned gate=0;gate<(guarded?5u:1u);++gate) {
            gateCase=gate;
            std::array<uint8_t,8>sent{},fading{};
            for(unsigned t=0;t<8;++t){m.write8(symbols.at("sent_codes")+t,0);m.write8(symbols.at("fading")+t,0);}
            m.write8(0x80000037,uint8_t(mode));m.write8(0x80000032,uint8_t(phones));
            for(unsigned frame=0;frame<3;++frame) {
                begins=ends=0;
                std::vector<uint8_t>before(128);for(unsigned i=0;i<before.size();++i)before[i]=uint8_t(i*13+7);
                if(clear)before[0x76]=before[0x77]=0; // $3b as a frame outside MATRIX leaves it
                auto expected=before;
                auto word=[&](unsigned at,unsigned value){expected[at]=uint8_t(value>>8);expected[at+1]=uint8_t(value);};
                std::array<uint8_t,8>routed{};
                for(unsigned t=0;t<8;++t) {
                    unsigned current=base==15?255:(base+3*t)%15;m.write8(0x80000c51+2*t,uint8_t(current));
                    if(current>13)current=0;
                    if(mode==2 && (!guarded || gate==1 || gate==2)) {
                        if(current==sent[t])fading[t]=0;
                        else if(!fading[t]){fading[t]=1;word(2+8*t,0);word(6+8*t,0);current=sent[t];}
                        else{sent[t]=uint8_t(current);fading[t]=0;}
                        routed[t]=uint8_t(current);
                    }
                }
                if(!guarded || gate==1 || gate==2) { if(mode==2) {
                    word(0x52,64);word(0x6e,77);word(0x70,phones>=128?0xff00+phones:phones);word(0x76,1);
                    for(unsigned half=0;half<2;++half){unsigned packed=0;for(unsigned t=0;t<4;++t)packed=16*packed+routed[4*half+t];word(0x72+2*half,packed);}
                } else word(0x76,0); }
                frameLeases=mode==2 || !clear; // MATRIX, or $3b to clear
                write(page,before);enter("page_levels");m68k_set_reg(cpu,M68K_REG_A2,page);m68k_set_reg(cpu,M68K_REG_D2,77);
                const unsigned started=instructions;run();
                if(base==0 && phones==64 && gate==(guarded?1u:0u) && frame==2 && mode!=1 && clear==(mode==0))
                    cost[mode==2?"MATRIX":"NORMAL, page $3b clear"]=instructions-started;
                assert(read(page,128)==expected);
                for(unsigned t=0;t<8;++t){assert(m.read8(symbols.at("sent_codes")+t)==sent[t]);assert(m.read8(symbols.at("fading")+t)==fading[t]);}
                assert(get(2)==77 && get(10)==page);
                for(unsigned r:{5u,6u,7u,9u,11u,12u,13u,14u})assert(get(r)==0x47070000+4*r);
                assert((get(3)&255u)==phones);
            }
        }
        // Independent whole-bank conversion oracle. Scoped: a switch into or
        // out of MATRIX runs the same conversion under one lease (granted:
        // gates 1/2; refused: 0, nothing changes); NORMAL <-> STUDIO stores
        // without a lease. CC 51 only after a successful End; redraw always.
        // No audio, timing or runtime retirement claim.
        for(unsigned oldMode=0;oldMode<3;++oldMode)for(unsigned newMode=0;newMode<3;++newMode)
        for(unsigned master=0;master<2;++master)for(unsigned mute=0;mute<2;++mute)
        for(unsigned currentBank:{0u,7u,15u})for(unsigned gate=0;gate<(guarded?3u:1u);++gate) {
            const bool involves=oldMode!=newMode && (oldMode==2 || newMode==2);
            const bool applies=!guarded || !involves || gate==1 || gate==2;
            modeLease=newMode==2?"matrix_enter":"matrix_leave";modeLeases=guarded && involves;
            struct Range{uint32_t at;std::vector<uint8_t> expected;};std::vector<Range> ranges;
            constexpr uint32_t bankStride=0x9b340,partStride=6322;
            const uint32_t cueBefore=0x00a50055;
            auto convert=[&](uint8_t level,uint8_t cue,unsigned track) {
                std::array<uint8_t,2> pair={level,cue};
                if(oldMode==newMode || (oldMode!=2 && newMode!=2))return pair;
                if(master && track==7){pair[1]=0;if(newMode!=2 && cue==13)pair[0]=0;return pair;}
                if(oldMode==2){unsigned code=cue>13?0:cue;pair[0]=(0x19ddu&(1u<<code))?level:0;pair[1]=(0x066au&(1u<<code))?level:0;}
                else if(oldMode==1){if(cue){if(level)pair[1]=3;else{pair[0]=cue;pair[1]=1;}}else pair[1]=0;}
                else if(!(cueBefore&(1u<<(16+track))))pair[1]=0;
                else if(!cue)pair[1]=mute?13:0;
                else if(!level || mute){pair[0]=cue;pair[1]=1;}
                else pair[1]=3;
                return pair;
            };
            std::array<bool,16> changed{};bool currentChanged=false;
            auto add=[&](uint32_t at,unsigned seed,bool live,unsigned bankIndex,bool cs1) {
                const unsigned bytes=live?16:partStride;
                std::vector<uint8_t> before(bytes);for(unsigned i=0;i<bytes;++i)before[i]=uint8_t(i*11+seed);
                const unsigned start=live?0:0x12;
                for(unsigned t=0;t<8;++t){before[start+2*t]=uint8_t((seed+31*t)%128);before[start+2*t+1]=uint8_t(oldMode==2?(seed+3*t)%16:(seed+17*t)%128);}
                auto expected=before;
                if(applies)for(unsigned t=0;t<8;++t){auto pair=convert(before[start+2*t],before[start+2*t+1],t);expected[start+2*t]=pair[0];expected[start+2*t+1]=pair[1];}
                if(expected!=before){if(cs1)currentChanged=true;else if(!live)changed[bankIndex]=true;}
                write(at,before);ranges.push_back({at,std::move(expected)});
            };
            for(unsigned b=0;b<16;++b){m.write32(bank+b*bankStride+0x9b332,0);for(unsigned p=0;p<4;++p){add(bank+b*bankStride+0x8ed80+p*partStride,11+b+p,false,b,false);add(bank+b*bankStride+0x9504a+p*partStride,31+b+p,false,b,false);}}
            for(unsigned p=0;p<4;++p){add(0x100a4ece + p*partStride,71+p,false,currentBank,true);add(0x100ab196+p*partStride,91+p,false,currentBank,true);}
            add(0x80000c50,51,true,currentBank,false);
            m.write32(0x46c82456,bank+currentBank*bankStride);m.write8(0x80000037,uint8_t(oldMode));m.write8(0x100b1497,uint8_t(oldMode));
            m.write8(0x80000034,uint8_t(master));m.write32(0x8000009c,mute);m.write32(0x80000008,cueBefore);m.write32(0x100b14d4,cueBefore);m.write32(0x100f8598,0);
            uint32_t cueExpected=cueBefore;
            std::vector<std::array<uint32_t,3>> expectedNotifications;
            if(applies && oldMode==2 && newMode==0){uint32_t bits=0;const auto live=read(0x80000c50,16);
                for(unsigned t=0;t<8;++t)if(!(master && t==7) && live[2*t+1]<=13 && (0x066au&(1u<<live[2*t+1])))bits|=1u<<(16+t);
                cueExpected=(cueBefore&0xff00ffff)|bits;
                if(!(guarded && gate==2))
                for(unsigned t=0;t<8;++t)if((cueExpected^cueBefore)&(1u<<(16+t)))expectedNotifications.push_back({t,51,unsigned(bool(cueExpected&(1u<<(16+t))))});}
            gateCase=gate;begins=ends=redraws=0;notifications.clear();enter("set_mode");m68k_set_reg(cpu,M68K_REG_D0,newMode);
            run();
            for(const auto &range:ranges)assert(read(range.at,unsigned(range.expected.size()))==range.expected);
            for(unsigned b=0;b<16;++b)assert(m.read32(bank+b*bankStride+0x9b332)==unsigned(changed[b] || (b==currentBank && currentChanged)));
            assert(m.read32(0x100f8598)==unsigned(changed[currentBank] || currentChanged));
            assert(m.read8(0x80000037)==(applies?newMode:oldMode) && m.read8(0x100b1497)==(applies?newMode:oldMode));
            assert(m.read32(0x80000008)==cueExpected && m.read32(0x100b14d4)==cueExpected);
            assert(notifications==expectedNotifications && redraws==1u);
            for(unsigned r:{2u,3u,4u,5u,6u,7u,10u,11u,12u,13u,14u})assert(get(r)==0x47070000+4*r);
        }
    }
    for(const auto &c:cost)std::printf("COST %s %s per call: %u instructions\n",module.c_str(),c.first.c_str(),c.second);
    std::printf("PASS actual ColdFire %s %s: %u calls, %u instructions, max held %u instructions, max mode %u instructions; source/fixture memory/register/stack oracle only\n",module.c_str(),guarded?"scoped-fixture":"original",calls,instructions,maxHeld,maxMode);
}

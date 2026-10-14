// SPDX-License-Identifier: GPL-3.0-or-later
// Private actual AB CF producer with explicit strong test functions.
// No real stable lock, generation resolver, encoded image or DSP activation.
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
static std::vector<uint8_t> load(const char *p){std::ifstream f(p,std::ios::binary);assert(f.good());return {(std::istreambuf_iterator<char>(f)),{}};}
int main(int argc,char **argv) {
    assert(argc==6);const uint32_t origin=std::stoul(argv[4],nullptr,0),render_bytes=std::stoul(argv[5]);
    constexpr uint32_t stack=0x46c7f920,stop=0x47300000,bank=0x400e21e0,record=0x80001c90;
    ot::Machine m(load(argv[1]));auto image=load(argv[2]);for(unsigned i=0;i<image.size();i++)m.write8(origin+i,image[i]);
    std::map<std::string,uint32_t> sy;std::ifstream f(argv[3]);std::string name;uint32_t value;while(f>>name>>value)sy[name]=origin+value;
    m.mapRegion(0x10000000,0x000b0000);m.mapRegion(0x100c0000,0x00040000);
    m.write32(0x46c82456,bank);m.write8(0x100b14cf,0);m.write8(0x100b14cc,0);
    uint32_t part=bank+0x8ed80;m.write8(part+0x22,1);m.write8(part+60,'A');m.write8(part+61,'B');m.write8(part+62,1);
    m.write32(sy.at("fixture_entry"),sy.at("ab_render"));
    unsigned calls=0,writes=0,denied=0,failed_ends=0,max_producer_instructions=0;bool active=false;
    auto watch=[&](uint32_t at,uint8_t,uint32_t,uint32_t pc){
        if(!active||pc<sy.at("ab_render")||pc>=sy.at("ab_render")+render_bytes||
           (at>=stack-0x1000&&at<stack+0x100))return;
        assert(m.read32(sy.at("fixture_phase"))==1);writes++;
    };
    m.addWriteWatch(0x40000400,0x48000000,watch);m.addWriteWatch(0x80000000,0x80010000,watch);
    for(uint32_t begin:{0u,2u,0xffffffffu,1u})for(uint32_t end:{0u,2u,0xffffffffu,1u}) {
        active=false;for(unsigned i=0;i<200;i++)m.write8(record+i,0xa5);
        m.write32(0x80001c80,record);m.write32(0x800062a8,0x80006500);m.write8(0x46104d0c,16);
        for(unsigned i=0;i<6;i++)m.write16(0x80006500+2*i,(12+i)<<8);
        for(unsigned i=6;i<12;i++)m.write8(0x80000830+i-6,12+i);
        m.write32(sy.at("fixture_begin_result"),begin);m.write32(sy.at("fixture_end_result"),end);
        m.write32(sy.at("fixture_phase"),0);m.write32(sy.at("fixture_begins"),0);m.write32(sy.at("fixture_ends"),0);
        const auto render_calls=m.read32(sy.at("ab_render_calls")),hits=m.read32(sy.at("ab_hits"));
        auto *cpu=m.getCpuState();for(unsigned r=0;r<15;r++)m68k_set_reg(cpu,m68k_register_t(M68K_REG_D0+r),0x47070000+4*r);
        m68k_set_reg(cpu,M68K_REG_SP,stack);m.write32(stack,stop);
        m.write32(stack+4,0);m.write32(stack+8,0);m.write32(stack+12,0);m.write32(stack+16,16);
        auto before=m.unmappedCount();m68k_set_reg(cpu,M68K_REG_PC,sy.at("ab_render"));active=true;unsigned budget=100000;
        unsigned producer_instructions=0;
        while(m.pc()!=stop&&budget--) {
            if(m.pc()>=sy.at("ab_render")&&m.pc()<sy.at("ab_render")+render_bytes&&
               m.read32(sy.at("fixture_phase"))==1)producer_instructions++;
            assert(m.step());
        }
        if(producer_instructions>max_producer_instructions)max_producer_instructions=producer_instructions;
        active=false;
        assert(m.pc()==stop&&m.unmappedCount()==before&&m68k_get_reg(cpu,M68K_REG_SP)==stack+4);
        for(unsigned r=2;r<8;r++)assert(m68k_get_reg(cpu,m68k_register_t(M68K_REG_D0+r))==0x47070000+4*r);
        for(unsigned r=2;r<7;r++)assert(m68k_get_reg(cpu,m68k_register_t(M68K_REG_A0+r))==0x47070020+4*r);
        assert(m.read32(sy.at("fixture_begins"))==1);
        uint32_t result=m68k_get_reg(cpu,M68K_REG_D0);
        if(begin!=1) {
            // Refused: the stock silent source fills this track's slot (header
            // n,0,1.0,0 and n zero pairs); no AB signature, counter or End.
            (void)result;denied++;assert(m.read32(0x80001c80)==record+144&&!m.read32(sy.at("fixture_ends")));
            assert(m.read32(sy.at("ab_render_calls"))==render_calls&&m.read32(sy.at("ab_hits"))==hits);
            assert(m.read32(record)==16&&!m.read32(record+4)&&m.read32(record+8)==0x04000000&&!m.read32(record+12));
            for(unsigned i=16;i<144;i++)assert(!m.read8(record+i));
            for(unsigned i=144;i<200;i++)assert(m.read8(record+i)==0xa5);
        } else {
            assert(m.read32(sy.at("fixture_ends"))==1&&m.read32(sy.at("fixture_phase"))==2);
            assert(m.read32(sy.at("ab_render_calls"))==render_calls+1&&m.read32(sy.at("ab_hits"))==hits+1);
            assert(m.read32(record)==0xab090000&&m.read32(record+4)==0x09090001&&m.read32(0x80001c80)==record+144);
            for(unsigned i=0;i<12;i++)assert(m.read16(record+16+2*i)==12+i);
            for(unsigned i=144;i<200;i++)assert(m.read8(record+i)==0xa5);
            assert(result==(end==1?0u:0xffffffffu));if(end!=1)failed_ends++;
        }
        calls++;
    }
    std::printf("{\"origin\":%u,\"calls\":%u,\"deniedBegins\":%u,\"failedEnds\":%u,\"producerWrites\":%u,\"maxProducerInstructionsInsideLease\":%u,\"fullBackendLeaseTimingQualified\":false,\"physicalTimingQualified\":false,\"exactLeaseArguments\":true,\"writesOnlyInsideLease\":true,\"noFailureReplay\":true,\"deniedSilentStockSource\":true,\"calleeRegistersAndStackExact\":true,\"explicitNativeTestFunctions\":true,\"productionLease\":false,\"encodedPackage\":false,\"hardware\":false,\"admission\":false}\n",origin,calls,denied,failed_ends,writes,max_producer_instructions);
}

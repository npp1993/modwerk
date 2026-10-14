// SPDX-License-Identifier: MIT
// Real compiled loader/context glue, synthetic package and RTOS memory only.
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
static constexpr uint32_t sp=0x46c7f920,packet=0x47010000,stop=0x47300000;
static void put(std::vector<uint8_t>& bytes,unsigned at,uint32_t value)
{ for (unsigned k=0;k<4;k++) bytes[at+k]=uint8_t(value>>(24-8*k)); }
struct Probe {
    ot::Machine machine;
    std::map<std::string,uint32_t> symbols;
    Probe(const std::vector<uint8_t>& image,const char *map):machine(image) {
        std::ifstream file(map); std::string address,type,name;
        while (file>>address>>type>>name) symbols[name]=std::stoul(address,nullptr,16);
        for (const char *name:{"prepare","publish","restore","retire"}) symbols[name]=symbols.at(std::string("modwerk_backend_")+name);
        assert(symbols.count("prepare") && symbols.count("publish") && symbols.count("retire"));
        constexpr struct { uint32_t tcb,stack; } tasks[]={
            {0x46c7fb0c,0x46c7ea20},{0x460bcc2c,0x460bc42c},{0x460d4f80,0x460d4780},
            {0x460d59d4,0x460d51d4},{0x460fab80,0x460fabd4},{0x460ffd44,0x460fdd44},
            {0x460e0e38,0x460dee38},{0x460ddde4,0x460d9de4},{0x46105508,0x4610555c},
            {0x46c7bed8,0x460d6de4},{0x46c7ae84,0x46c7aed8}};
        for (auto task:tasks) { machine.write32(task.tcb,0); machine.write32(task.tcb+0x48,task.stack+8); }
        machine.write32(0x800068fc,tasks[0].tcb);
        for (unsigned i=0;i<8;i++) machine.write32(0x800068dc+4*i,0);
        machine.write32(0x800068dc,tasks[0].tcb); machine.write32(tasks[0].tcb,tasks[0].tcb);
#ifdef MODWERK_MACHINE_DECLARATION_TEST
        machine.mapRegion(0x10000000,0x000b0000);machine.mapRegion(0x100c0000,0x00040000);
        machine.write32(0x46c82456,0x400e21e0);
        call("fixture_clear_declarations");
#endif
    }
    uint32_t call(const char *name,std::vector<uint32_t> args={},uint32_t register_ref=0,uint32_t stack_ref=0) {
        auto *cpu=machine.getCpuState();
        for (unsigned i=0;i<15;i++) m68k_set_reg(cpu,m68k_register_t(M68K_REG_D0+i),0);
        m68k_set_reg(cpu,M68K_REG_D2,register_ref); m68k_set_reg(cpu,M68K_REG_SP,sp);
        machine.write32(sp,stop);
        for (unsigned i=0;i<args.size();i++) machine.write32(sp+4+4*i,args[i]);
        machine.write32(sp+66,stack_ref); // packed reference, not a local loader variable
        m68k_set_reg(cpu,M68K_REG_PC,symbols.at(name));
        unsigned budget=5000000;
        while (machine.pc()!=stop && budget--) assert(machine.step());
        if (machine.pc()!=stop) std::fprintf(stderr,"%s did not return at %x: %s\n",name,machine.pc(),machine.why().c_str());
        assert(machine.pc()==stop);
        return m68k_get_reg(cpu,M68K_REG_D0);
    }
    bool prepare(bool group,bool review=true,unsigned state=1,unsigned parameter=1,unsigned tag=0) {
#ifndef MODWERK_MACHINE_DECLARATION_TEST
        (void)review;(void)state;(void)parameter;(void)tag;
#endif
        std::vector<uint8_t> bytes(group?108:76,0);
        bytes[0]='M';bytes[1]='W';bytes[2]='R';bytes[3]='M';bytes[5]=8;bytes[7]=group?4:0;
        put(bytes,8,group?32:0);put(bytes,28,81);
        if (group) { bytes[50]='F';bytes[51]='M';bytes[67]=1;
            bytes[76]='M';bytes[77]='W';bytes[78]='M';bytes[79]='G';bytes[80]=1;bytes[81]=4; }
#ifdef MODWERK_MACHINE_DECLARATION_TEST
        if(group) { bytes[66]=parameter>>8;bytes[67]=parameter;bytes[107]=tag; }
#endif
        for (unsigned i=0;i<bytes.size();i++) machine.write8(packet+i,bytes[i]);
#ifdef MODWERK_MACHINE_DECLARATION_TEST
        if(group && review) call("fixture_review_package",{packet,uint32_t(bytes.size()),state,parameter});
#endif
        return call("prepare",{0,packet,uint32_t(bytes.size())})==1;
    }
};
int main(int argc,char **argv) {
    assert(argc==3); std::ifstream file(argv[1],std::ios::binary); assert(file.good());
    std::vector<uint8_t> image((std::istreambuf_iterator<char>(file)),{});assert(!image.empty());
    Probe p(image,argv[2]);
#ifdef MODWERK_MACHINE_DECLARATION_TEST
    assert(!p.prepare(true,false) && p.call("modwerk_runtime_refusal")==1 && p.call("modwerk_runtime_active")==0);
#endif
    assert(p.prepare(true) && p.call("publish",{0})==1 && p.call("retire",{0})==1);
    uint32_t group=p.call("fixture_group_image"),free=p.call("modwerk_runtime_free",{0});assert(group);
#ifdef MODWERK_MACHINE_DECLARATION_TEST
    assert(!p.prepare(true,true,2,1,1) && p.call("modwerk_runtime_refusal")==3);
    assert(!p.prepare(true,true,1,2,2) && p.call("modwerk_runtime_refusal")==3);
    assert(!p.prepare(true,false,1,1,3) && p.call("modwerk_runtime_refusal")==1);
    // Actual board helper reads cache roots and all four Part regions. Both
    // mapped aliases and every retained-layout failure preserve the baseline.
    for(uint32_t alias:{0u,0x08000000u}) {
        p.machine.write32(0x46c7d8de,group+16-(alias?0x08000000u:0));
        assert(!p.prepare(false) && p.call("modwerk_runtime_refusal")==7 && p.call("fixture_group_image")==group);
        p.machine.write32(0x46c7d8de,0);
    }
    p.machine.write8(0x100a4eceu+0x2fdu,1);
    assert(!p.prepare(false) && p.call("modwerk_runtime_refusal")==7 && p.call("modwerk_runtime_free",{0})==free);
    p.machine.write8(0x100a4eceu+0x2fdu,0);
#endif
    for (unsigned context=0;context<4;context++) for (unsigned alias=0;alias<2;alias++)
        for (uint32_t offset:{8u,16u,20u,31u}) {
            uint32_t ref=group+offset-(alias?0x08000000u:0);
            assert(p.prepare(false));
            if (context==2) p.machine.write32(0x460bcc2c+0x0c,ref); // another task's saved d0
            if (context==3) p.machine.write32(0x460bc42c+12,ref); // another task's live stack
            assert(p.call("publish",{0},context==0?ref:0,context==1?ref:0)==0);
            assert(p.call("modwerk_runtime_refusal")==5 && p.call("fixture_group_image")==group);
            assert(p.call("modwerk_runtime_free",{0})==free && p.call("discard",{0})==1);
            p.machine.write32(0x460bcc2c+0x0c,0);p.machine.write32(0x460bc42c+12,0);
        }
    assert(p.prepare(false));p.machine.write32(0x800068dc,0x47000000);
    assert(p.call("publish",{0})==0 && p.call("fixture_group_image")==group && p.call("discard",{0})==1);
    p.machine.write32(0x800068dc,0x46c7fb0c);
    // Replacement and Undo keep the exact original extent available. A held
    // reference into the trial refuses Undo until its caller context clears.
    assert(p.prepare(true) && p.call("publish",{0})==1);
    uint32_t trial=p.call("fixture_group_image");assert(trial && trial!=group);
    assert(p.call("restore",{0},trial+16)==0 && p.call("fixture_group_image")==trial);
    assert(p.call("restore",{0})==1 && p.call("fixture_group_image")==group);
    assert(p.call("retire",{0})==1 && p.call("modwerk_runtime_free",{0})==free);
    assert(p.prepare(false) && p.call("publish",{0})==1 && p.call("retire",{0})==1);
    assert(p.call("modwerk_runtime_active")==0 && p.call("modwerk_runtime_free",{0})==262144);
}

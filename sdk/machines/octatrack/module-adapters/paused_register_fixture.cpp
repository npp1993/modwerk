// SPDX-License-Identifier: MIT
// Execute only freshly compiled authored runtime glue on the ColdFire port.
// No firmware input, boot, DSP, USB or hardware access.
#include <cassert>
#include <cstdio>
#include <fstream>
#include <iterator>
#include <string>
#include <vector>
#include "machine.h"
#include "mc68k/Musashi/m68k.h"
#include "mc68k/cpuState.h"

static constexpr struct { uint32_t tcb, stack, size; } tasks[] = {
    {0x46c7fb0c,0x46c7ea20,0x1000}, {0x460bcc2c,0x460bc42c,0x800}, {0x460d4f80,0x460d4780,0x800},
    {0x460d59d4,0x460d51d4,0x800}, {0x460fab80,0x460fabd4,0x2000}, {0x460ffd44,0x460fdd44,0x2000},
    {0x460e0e38,0x460dee38,0x2000}, {0x460ddde4,0x460d9de4,0x4000}, {0x46105508,0x4610555c,0x2000},
    {0x46c7bed8,0x460d6de4,0x2000}, {0x46c7ae84,0x46c7aed8,0xff4},
};
static constexpr uint32_t output=0x47010000, snapshot=output+0x100, stop=0x47300000;

static void run(const std::vector<uint8_t>& image, uint32_t entry, unsigned current, unsigned max, unsigned bad)
{
    ot::Machine m(image);
    auto *cpu=m.getCpuState();
    const uint32_t sp=tasks[current].stack+tasks[current].size-256;
    uint32_t expected[16];
    for (unsigned i=0;i<16;i++) {
        expected[i]=i==15?sp:0x40010008+4*i;
        m68k_set_reg(cpu,m68k_register_t(M68K_REG_D0+i),expected[i]);
    }
    for (unsigned i=0;i<11;i++) {
        m.write32(tasks[i].tcb,0);
        m.write32(tasks[i].tcb+0x48,tasks[i].stack+8);
        for (unsigned r=0;r<15;r++) m.write32(tasks[i].tcb+0x0c+4*r,0x40020000+4*r);
    }
    m.write32(0x800068fc,bad==1?0x47000000:tasks[current].tcb);
    for (unsigned i=0;i<8;i++) m.write32(0x800068dc+4*i,0);
    m.write32(0x800068dc,tasks[current].tcb);
    m.write32(tasks[current].tcb,tasks[current].tcb);
    if (bad==2) m.write32(0x800068dc,0x47000000);
    if (bad==3) m.write32(tasks[(current+1)%11].tcb+0x48,tasks[(current+1)%11].stack-4);
    if (bad==4) m.write32(tasks[(current+1)%11].tcb+0x48,tasks[(current+1)%11].stack+tasks[(current+1)%11].size+4);
    m.write32(output+0x400,0x13579bdf); m.write32(output+0x404,max);
    m.write32(sp,stop); m.write32(sp+4,output+0x400); m.write32(sp+8,output); m.write32(sp+12,max);
    m68k_set_reg(cpu,M68K_REG_PC,entry);
    unsigned budget=10000;
    while (m.pc()!=stop && budget--) assert(m.step());
    assert(m.pc()==stop);
    for (unsigned r=0;r<16;r++) {
        if (m.read32(snapshot+4*r)!=expected[r])
            std::fprintf(stderr,"entry=%x current=%u max=%u bad=%u register=%u got=%x expected=%x\n",
                         entry,current,max,bad,r,m.read32(snapshot+4*r),expected[r]);
        if (m.read32(snapshot+4*r)!=expected[r])
            std::fprintf(stderr,"count=%x captured=%x contextArg=%x originalArg=%x magic=%x\n",
                         m68k_get_reg(cpu,M68K_REG_D0),m.read32(sp-64),m.read32(sp-68),m.read32(sp-72),m.read32(output+0x400));
        assert(m.read32(snapshot+4*r)==expected[r]);
    }
    for (unsigned r=2;r<15;r++) if (r!=8 && r!=9)
        assert(m68k_get_reg(cpu,m68k_register_t(M68K_REG_D0+r))==expected[r]);
    assert(m68k_get_reg(cpu,M68K_REG_SP)==sp+4);
    assert(m.read32(sp+4)==output+0x400 && m.read32(sp+8)==output && m.read32(sp+12)==max);
    unsigned count=m68k_get_reg(cpu,M68K_REG_D0);
    if (bad || max<22) { assert(count==max+1); return; }
    assert(count==22);
    assert(m.read32(output)==sp-64 && m.read32(output+4)==sp);
    unsigned n=1;
    for (unsigned i=0;i<11;i++) {
        uint32_t from=m.read32(output+8*n),to=m.read32(output+8*n+4); ++n;
        assert(to==tasks[i].stack+tasks[i].size);
        if (i==current) assert(from==sp);
        else {
            assert(from==tasks[i].stack+8);
            assert(m.read32(output+8*n)==tasks[i].tcb+0x0c);
            assert(m.read32(output+8*n+4)==tasks[i].tcb+0x4c); ++n;
        }
    }
    assert(n==count);
}
int main(int argc,char **argv)
{
    assert(argc==4);
    std::ifstream source(argv[1],std::ios::binary);
    assert(source.good());
    std::vector<uint8_t> image((std::istreambuf_iterator<char>(source)),{});
    assert(!image.empty());
    for (unsigned entry=0;entry<2;entry++)
        for (unsigned current=0;current<11;current++) {
            uint32_t pc=std::stoul(argv[2+entry],nullptr,16);
            run(image,pc,current,22,0);
            run(image,pc,current,32,0);
            run(image,pc,current,21,0);
            for (unsigned bad=1;bad<=4;bad++) run(image,pc,current,32,bad);
        }
}

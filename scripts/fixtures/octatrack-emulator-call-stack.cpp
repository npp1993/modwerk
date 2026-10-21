// SPDX-License-Identifier: GPL-3.0-or-later
// Authored ColdFire program; no firmware, card image or project fixture.
#include "machine.h"
#include "rtos.h"
#include <cstdio>
#include <vector>
int main() {
    // GNU m68k-elf-as -mcpu=54455:
    // movel %sp@(4),%d0; addl %sp@(8),%d0; rts
    const std::vector<uint8_t> program{0x20,0x2f,0,4,0xd0,0xaf,0,8,0x4e,0x75};
    ot::Machine machine(program);
    ot::Rtos rtos(machine);
    const uint32_t stack=0x46100000;
    machine.setA7(stack);machine.setPC(ot::g_mainSpin);
    uint32_t result=0;unsigned failures=0;
    for(unsigned i=0;i<128;++i) {
        if(!rtos.callAsMain(0x40000400,{17,25},result,1000) || result!=42) {
            std::printf("FAIL argument/result at %u: %s\n",i,rtos.why().c_str());return 1;
        }
        if(machine.getA7()!=stack) {
            if(!failures)std::printf("FAIL caller stack %#x became %#x\n",stack,machine.getA7());
            ++failures;
        }
    }
    std::printf("%s: 128 executed two-argument calls, %u stack mismatches\n",failures?"FAIL":"PASS",failures);
    return failures?1:0;
}

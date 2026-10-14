// SPDX-License-Identifier: GPL-3.0-or-later
#include "idle-range.h"
#include <cassert>
#include <map>
int main() {
    std::map<uint32_t,uint16_t> code{{0,0x4eb9},{6,0x2439},{12,0x2039},{18,0x2200},{20,0x9282},
        {22,0x2400},{24,0xb2b9},{30,0x62ec},{32,0xd3b9},{38,0x60e4}};
    auto read = [&](uint32_t at) { return code[at]; };
    const auto range = modwerkIdleRange(0, read);
    assert(range.first == 12 && range.second == 40); // init is executed; only the loop parks
    code[30] = 0x6200; // a branch elsewhere cannot establish these idle bounds
    assert(modwerkIdleRange(0, read).second == 0);
    code.clear(); code[0] = 0x60fe; // stock bras . stays under the original stock-PC check
    assert(modwerkIdleRange(0, read).second == 0);
}

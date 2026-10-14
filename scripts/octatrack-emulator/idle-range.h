// SPDX-License-Identifier: GPL-3.0-or-later
// Recognize only Modwerk's own status.s idle loop, excluding its initialization.
// A guessed window from a detour entry can suppress the displaced stock call.
#pragma once
#include <cstdint>
#include <utility>
template<class Read16>
std::pair<uint32_t, uint32_t> modwerkIdleRange(uint32_t entry, Read16 read)
{
    // jsr abs.l; move.l DTCN3,d2; then the loop's instructions. Operands
    // naming relocated counters vary; all branch destinations must be the loop.
    const struct { uint32_t at; uint16_t opcode; } words[] = {
        {0, 0x4eb9}, {6, 0x2439}, {12, 0x2039}, {18, 0x2200},
        {20, 0x9282}, {22, 0x2400}, {24, 0xb2b9}, {30, 0x62ec},
        {32, 0xd3b9}, {38, 0x60e4},
    };
    for (const auto& word : words) if (read(entry + word.at) != word.opcode) return {0, 0};
    return {entry + 12, entry + 40};
}

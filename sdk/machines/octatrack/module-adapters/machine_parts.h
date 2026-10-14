/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef MODWERK_MACHINE_PARTS_H
#define MODWERK_MACHINE_PARTS_H
#include <stdint.h>
typedef int (*machine_part_read)(void *, uint32_t, uint8_t *, unsigned);
enum machine_part_result {
    MACHINE_PART_CLEAR=0, MACHINE_PART_RETAINED=1, MACHINE_PART_UNKNOWN=2,
    MACHINE_PART_FM_LEG=3, MACHINE_PART_FM_MARKER=4
};
/* Explicit retained-layout reasons distinguish signed ownership from FM's
 * ordinary-track LEG byte and legacy FLEX sample-name marker. LEG may be
 * indistinguishable from a saved stock TRIG value, including the master;
 * conservative beta removal refuses rather than guessing its meaning.
 * Four working and four saved RAM Parts plus their eight SRAM mirrors.
 * RAM accepts either bank alias and preserves it for reads; SRAM addresses
 * stay fixed. This is a removal check, not an installation/coexistence gate.
 * These exact 1.40C layouts do not read disk-only banks. */
int machine_part_lifetime(machine_part_read, void *, uint32_t bank, unsigned dropped);
/* Any machine by its Part signature (sig[0], sig[1], version lo..hi) on a FLEX or STATIC track of the same copies:
 * CLEAR, RETAINED or UNKNOWN. The removal check for a contributed machine without its own retirement. */
int machine_part_signature(machine_part_read, void *, uint32_t bank, const uint8_t sig[2], uint8_t lo, uint8_t hi);
#endif

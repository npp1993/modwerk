/* SPDX-License-Identifier: MIT */
#include "machine_admission.h"
/* Fixed, nonzero, address-stable storage. Private filling must preserve its
 * length and every byte/symbol outside this storage and the base identity. */
#ifdef __APPLE__
#define DECLARATION_SECTION "__TEXT,__mwmd"
#else
#define DECLARATION_SECTION ".rodata.machine_declarations"
#endif
const uint8_t modwerk_machine_declarations[MACHINE_DECLARATION_BYTES]
    __attribute__((used, aligned(4), section(DECLARATION_SECTION))) =
    {'M','W','M','D',MACHINE_DECLARATION_REVISION,0,MACHINE_DECLARATION_CAPACITY,0};

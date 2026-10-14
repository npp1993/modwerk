/* SPDX-License-Identifier: MIT */
#include "table_declarations.h"
#ifdef __APPLE__
#define DECLARATION_SECTION "__TEXT,__mwtd"
#else
#define DECLARATION_SECTION ".rodata.table_declarations"
#endif
/* A nonzero, fixed-size object remains in the linked image. The private
 * collector may fill only these reserved bytes after independent review;
 * filling must never relink, move the arena or change package stock guards. */
const uint8_t modwerk_table_declarations[TABLE_DECLARATION_BYTES]
__attribute__((used, aligned(4), section(DECLARATION_SECTION))) = {
    'M','W','T','D',1,0,TABLE_DECLARATION_CAPACITY
};

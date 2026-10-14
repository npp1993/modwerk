/* SPDX-License-Identifier: MIT */
#ifndef MODWERK_TABLE_DECLARATIONS_H
#define MODWERK_TABLE_DECLARATIONS_H
/* Private board trust storage, reserved before any package is composed.
 * Uploaded packages cannot populate it. Empty storage admits no table owner.
 * No public envelope flag or capability is introduced by this reservation. */
#include <stdint.h>
#define TABLE_DECLARATION_HEADER 16u
#define TABLE_DECLARATION_CAPACITY 24u
#define TABLE_DECLARATION_RECORD 60u
#define TABLE_DECLARATION_BYTES (TABLE_DECLARATION_HEADER + TABLE_DECLARATION_CAPACITY * TABLE_DECLARATION_RECORD)
extern const uint8_t modwerk_table_declarations[TABLE_DECLARATION_BYTES];
#endif

/* SPDX-License-Identifier: MIT */
#ifndef MODWERK_MACHINE_ADMISSION_H
#define MODWERK_MACHINE_ADMISSION_H
#include "loader.h"
#include "machine_lifetime.h"
#define MACHINE_DECLARATION_REVISION 2u
#define MACHINE_DECLARATION_CAPACITY 24u
#define MACHINE_OPTIONAL_QUANTIZER 1u
#define MACHINE_ANALOG_BD 2u
#define MACHINE_DECLARATION_HEADER 16u
#define MACHINE_DECLARATION_RECORD 44u
#define MACHINE_DECLARATION_BYTES (MACHINE_DECLARATION_HEADER + MACHINE_DECLARATION_CAPACITY * MACHINE_DECLARATION_RECORD)
/* Reserved once, before linking/composing packages. The private build may fill
 * its bytes from separately reviewed declarations; no uploaded package changes
 * this trust table. The default valid empty table admits no machine group. */
extern const uint8_t modwerk_machine_declarations[MACHINE_DECLARATION_BYTES];
/* Caller holds the machine's stable lock. The package digest is the complete
 * encoded package retained by loader preparation, not the relocated image.
 * This contract covers MWMG v1 machine groups only, never table splices/DSP
 * ownership. Paused registers/stacks and stock site guards remain loader gates.
 * Unknown foreign roots or saved layouts refuse. */
/* Returns -1 for an unauthenticated group, otherwise the reviewed optional
 * Quantizer participant bit. Ordinary packages return zero. FM needs QZ
 * regardless of this bit; no mask-only optional ownership inference. */
/* Returns the explicit trusted AB bit, never readiness or admission. Current
 * production admission refuses every from/to AB until controller association,
 * distinct AB Part roots and UI restoration are bound under the actual lock. */
int machine_metadata_analog_bd(const uint8_t table[MACHINE_DECLARATION_BYTES],const struct runtime_dsp *);
int machine_metadata_optional_quantizer(const uint8_t table[MACHINE_DECLARATION_BYTES],const struct runtime_dsp *);
int machine_metadata_admission(const uint8_t table[MACHINE_DECLARATION_BYTES],
    const struct runtime_dsp *from, const struct runtime_dsp *to,
    machine_memory_read read, void *context, uint32_t bank);
#endif

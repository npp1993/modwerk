/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef MODWERK_RUNTIME_CONTEXT_H
#define MODWERK_RUNTIME_CONTEXT_H
/* ColdFire backend-entry wrappers capture before a C prologue can reuse a
 * register. The 64-byte snapshot belongs to this call and survives interrupts
 * and nested calls. Its entry SP excludes loader bookkeeping from the scan;
 * caller frames, return addresses and all original registers remain included.
 * args copies the original arguments after the additional context argument. */
#define RUNTIME_CONTEXT_WRAPPER(name, target, args, release) \
__asm__( ".globl " #name "\n.type " #name ",@function\n" #name ":\n" \
    "lea %sp@(-64),%sp\nmovem.l %d0-%d7/%a0-%a7,%sp@\n" \
    "lea %sp@(64),%a0\nmove.l %a0,%sp@(60)\n" \
    "movea.l %sp,%a0\nmove.l %a0,%sp@-\n" args \
    "jsr " #target "\nlea %sp@(" #release "),%sp\nrts\n" \
    ".size " #name ",.-" #name "\n")
#define RUNTIME_CONTEXT_ONE "move.l %sp@(72),%sp@-\n"
#define RUNTIME_CONTEXT_THREE "move.l %sp@(80),%sp@-\nmove.l %sp@(80),%sp@-\nmove.l %sp@(80),%sp@-\n"
#endif

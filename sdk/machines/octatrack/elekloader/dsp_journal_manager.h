/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef MODWERK_DSP_JOURNAL_MANAGER_H
#define MODWERK_DSP_JOURNAL_MANAGER_H
#include <stdint.h>
#include "journal.h"
/* The manager journal (resident_journal.py's transform of the generated
 * manager.c) and the board journal adapter meet only here. Every call runs
 * under the retained stable lock. Returns: 1 exact, 0 definite refusal with
 * nothing changed, -1 unknown (both generations stay held, never retried). */
struct mw_manager_core_receipt {
    uint32_t job_ticket, job_generation, pool_base, pool_words;
    uint16_t first_sequence, last_sequence, acknowledged_sequence;
    uint16_t code_offset, code_words;
    uint8_t released; /* backend job storage release checked */
};
/* Freeze manager placement for this journal generation: the whole-transport
 * lease, live/target per-core placements and Part desired slots. */
int mw_manager_journal_freeze(uint32_t journal_generation);
/* Stage one row's owned DSP work (new contiguous target, predecessor kept). */
int mw_manager_journal_stage(uint32_t journal_generation, const struct runtime_journal_view *row, int reverse);
/* Advance owned upload/BIND/BYPASS jobs: 1 all staged rows ACKed and
 * released, 0 still progressing, -1 failed or unknown. */
int mw_manager_journal_step(uint32_t journal_generation);
/* Nonmutating: the exact completed receipt for this row. *required is the
 * core mask; 1 with *required 0 is a positively checked no-job transition. */
int mw_manager_journal_receipt(uint32_t journal_generation, const struct runtime_journal_view *row, int reverse,
                               uint8_t *required, struct mw_manager_core_receipt out[2]);
/* Keep, in the trial: forward finalization of exactly the journal's rows, each a fresh install that placed and
 * rebound nothing (no predecessor to free). Any row retiring a predecessor refuses (0, nothing changed). */
int mw_manager_journal_accept(uint32_t journal_generation, const struct runtime_journal_view *rows, unsigned n);
/* Release the lease after an accepted Keep or exact reverse completion, once the journal is idle. */
int mw_manager_journal_release(uint32_t journal_generation);
#endif

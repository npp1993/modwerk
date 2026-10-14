/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef MODWERK_DSP_JOURNAL_H
#define MODWERK_DSP_JOURNAL_H
#include "journal.h"
/* Borrowed only while the real stable lock remains held. This is a board
 * transition ledger receipt, never a wire format or a host readiness claim.
 * The adapter records exact completed owned jobs and their checked releases;
 * a zero required mask still needs a positively checked no-job transition. */
struct modwerk_journal_commit_fact {
    struct runtime_journal_view row;
    uint32_t ticket, generation, map_generation;
    uint32_t job_ticket[2], job_generation[2], pool_base[2], pool_words[2];
    uint16_t first_sequence[2], last_sequence[2], acknowledged_sequence[2];
    uint16_t code_offset[2], code_words[2];
    uint8_t reverse, required, touched, confirmed, released;
    uint8_t catalogue_handle; /* exact target handle, 255 for a CF-only/removal target */
    uint8_t catalogue_target; /* reverse of an unpublished row: target already lives */
};
/* Only the actual board adapter may answer from its stored transition. It
 * must bind source/owner/resource identities and every owned packet ACK and
 * storage release; absent/unknown authority returns zero. Consume exactly
 * once, before any catalogue/page/map writes. Neither entry schedules work. */
int modwerk_machine_journal_commit_ready(const struct runtime_journal_view *,int,
    struct modwerk_journal_commit_fact *);
int modwerk_machine_journal_commit_consume(const struct modwerk_journal_commit_fact *);
/* Nonmutating board inspection under the stable lock; -1 absent, -2 unknown. */
int modwerk_dsp_catalogue_handle(uint32_t module);
#endif

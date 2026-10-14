/* SPDX-License-Identifier: GPL-3.0-or-later
 * Octatrack board adapter for the volatile publication journal (journal.h).
 * Its only authority is its own transition ledger: exact manager-journal
 * receipts (dsp_journal_manager.h) for the loader's exact rows, generation and
 * map, each consumable once. Keep accepts fresh installs only; nothing here
 * writes the saved set (volatile_service.c gives modset.c the kept set).
 * Closed by default: no public recipe defines
 * MODWERK_JOURNAL_BOARD_ENABLED and the association table is empty. Any
 * unknown manager answer poisons the ledger until reboot: both generations stay
 * held and nothing is retried. Every entry runs under the retained stable lock.
 * No controller job is driven here: no reviewed controller declaration or
 * provider exists (controller_transport.h), and stock hooks refuse enable. */
#include <stddef.h>
#include "dsp_journal.h"
#include "dsp_journal_manager.h"
#include "fxmap.h"

#ifndef MODWERK_JOURNAL_BOARD_ENABLED
#define MODWERK_JOURNAL_BOARD_ENABLED 0
#endif
/* Board-compiled reviewed rows {encoded package SHA-256, module, ascending
 * canonical participant ids, zero-filled}; a canonical group holds at most its
 * three members, Quantizer and Analog BD. Sized by rows; the zero sentinel is
 * never trusted. None is reviewed yet, so every bundle record is refused. */
#define JOURNAL_PARTICIPANTS 5u
struct journal_association { uint8_t package_sha256[MU_DIGEST_BYTES]; uint32_t module, participants[JOURNAL_PARTICIPANTS]; };
#ifndef MW_REVIEWED_JOURNAL_ASSOCIATIONS
#define MW_REVIEWED_JOURNAL_ASSOCIATIONS /* none */
#endif
#ifndef MW_JOURNAL_ASSOCIATION_STORAGE
#define MW_JOURNAL_ASSOCIATION_STORAGE const /* host fixtures only: synthetic rows take run-time digests */
#endif
static MW_JOURNAL_ASSOCIATION_STORAGE struct journal_association associations[] = { MW_REVIEWED_JOURNAL_ASSOCIATIONS {{0}, 0, {0}} };

enum { TOUCHED = 1, PUBLISHED = 2 };
static struct {
    struct modwerk_journal_commit_fact fact; /* the single stored record, valid while ready */
    uint32_t admitted, generation, ticket, job_ticket[2]; /* generation: the manager lease's, 0 none */
    uint32_t module[RUNTIME_JOURNAL_ROWS];
    uint8_t state[RUNTIME_JOURNAL_ROWS];
    uint8_t rows, work, reverse, complete, ready, poisoned; /* work: staged row + 1 */
} board;

static int __attribute__((noinline)) same(const void *a, const void *b, unsigned n)
{ const uint8_t *x = a, *y = b; for (unsigned i = 0; i < n; ++i) if (x[i] != y[i]) return 0; return 1; }
/* These spans hold no padding on the host or ColdFire ABI. */
#define OWNER_BYTES (offsetof(struct runtime_owner, package_sha256) + MU_DIGEST_BYTES)
#define FACT_SCALARS (offsetof(struct modwerk_journal_commit_fact, catalogue_target) + 1u - \
                      offsetof(struct modwerk_journal_commit_fact, ticket))
static int same_view(const struct runtime_journal_view *a, const struct runtime_journal_view *b)
{
    return a->module == b->module && a->position == b->position && a->from == b->from && a->to == b->to &&
        same(&a->before, &b->before, OWNER_BYTES) && same(&a->after, &b->after, OWNER_BYTES) &&
        same(a->package_sha256, b->package_sha256, MU_DIGEST_BYTES);
}
static uint32_t generation_in(unsigned phase)
{
    struct runtime_journal_progress p;
    modwerk_runtime_journal_snapshot(&p);
    return p.phase == phase ? p.generation : 0;
}
static unsigned row_of(uint32_t module)
{ unsigned i = 0; while (i < board.rows && board.module[i] != module) ++i; return i; }
static const struct journal_association *declared(uint32_t module, const uint8_t *digest)
{
    const struct journal_association *found = 0;
    for (unsigned i = 0; module && i + 1u < sizeof associations / sizeof *associations; ++i)
        if (associations[i].module == module && same(associations[i].package_sha256, digest, MU_DIGEST_BYTES)) {
            if (found) return 0; /* a duplicate identity could hide another participant set */
            found = &associations[i];
        }
    return found;
}

int modwerk_machine_journal_enabled(void) { return MODWERK_JOURNAL_BOARD_ENABLED == 1; }
/* Host masks are claims: the exact declared participant list must match. */
int modwerk_machine_journal_association(uint32_t module, const uint8_t digest[MU_DIGEST_BYTES], const uint32_t *ids, unsigned n)
{
    const struct journal_association *a = digest && ids && n && n <= JOURNAL_PARTICIPANTS ? declared(module, digest) : 0;
    for (unsigned k = 0; a && k < JOURNAL_PARTICIPANTS; ++k) if (a->participants[k] != (k < n ? ids[k] : 0u)) return 0;
    return a != 0;
}
/* No board mechanism holds PLAY/REC closed (modwerk_machine_stopped() is an
 * observation, not a latch), so a running trial is never granted and there is
 * never a released latch to regain. Neither direction touches the transport. */
int modwerk_machine_journal_trial(int running) { return running == 0; }

/* A lease still held from an earlier generation (a refused release) closes every later one. */
int modwerk_machine_journal_admit(const struct runtime_journal_view *rows, unsigned n)
{
    uint32_t generation = generation_in(RJ_RECEIVING);
    if (board.poisoned || board.generation || !generation || !rows || !n || n > RUNTIME_JOURNAL_ROWS) return 0;
    for (unsigned i = 0; i < n; ++i) if (!declared(rows[i].module, rows[i].package_sha256)) return 0;
    board.admitted = generation; board.rows = (uint8_t)n; board.work = board.ready = 0;
    for (unsigned i = 0; i < n; ++i) board.module[i] = rows[i].module, board.state[i] = 0;
    return 1;
}
/* The ledger record: the manager's exact completed receipt for this row. */
static int record(const struct runtime_journal_view *r, int reverse, unsigned row)
{
    uint8_t required = 0; struct mw_manager_core_receipt out[2] = {{0}};
    if (mw_manager_journal_receipt(board.generation, r, reverse, &required, out) != 1 || required > 3u ||
        board.ticket == UINT32_MAX) return 0;
    struct modwerk_journal_commit_fact *f = &board.fact;
    *f = (struct modwerk_journal_commit_fact){0};
    f->row = *r; f->ticket = ++board.ticket; f->generation = board.generation;
    f->map_generation = modwerk_fxmap_checked_generation();
    f->reverse = (uint8_t)reverse; f->required = f->touched = f->confirmed = required;
    for (unsigned c = 0; c < 2u; ++c) {
        const struct mw_manager_core_receipt *k = &out[c];
        if (required >> c & 1u) {
            /* Whole ACKed range and checked storage release; a ticket never repeats. */
            if (!k->released || !k->job_ticket || k->job_ticket <= board.job_ticket[c] || !k->job_generation ||
                !k->first_sequence || k->first_sequence > k->last_sequence || k->acknowledged_sequence != k->last_sequence) return 0;
            board.job_ticket[c] = k->job_ticket; f->released |= (uint8_t)(1u << c);
        } else if (k->job_ticket || k->job_generation || k->first_sequence || k->last_sequence ||
                   k->acknowledged_sequence || k->code_offset || k->code_words || k->released) return 0;
        f->job_ticket[c] = k->job_ticket; f->job_generation[c] = k->job_generation;
        f->pool_base[c] = k->pool_base; f->pool_words[c] = k->pool_words;
        f->first_sequence[c] = k->first_sequence; f->last_sequence[c] = k->last_sequence;
        f->acknowledged_sequence[c] = k->acknowledged_sequence;
        f->code_offset[c] = k->code_offset; f->code_words[c] = k->code_words;
    }
    const struct runtime_dsp *to = reverse ? r->from : r->to;
    int had = modwerk_dsp_catalogue_handle(r->module);
    if (had == -2) return 0;
    f->catalogue_handle = (uint8_t)(!to->count ? 255u : had >= 0 ? (unsigned)had : to->id);
    f->catalogue_target = (uint8_t)(reverse && !(board.state[row] & PUBLISHED));
    board.ready = 1;
    return 1;
}
enum runtime_journal_observation modwerk_machine_journal_transition(const struct runtime_journal_view *r, int reverse, uint8_t masks[3])
{
    unsigned row = row_of(r->module), key = row + 1u;
    int s;
    masks[0] = masks[1] = masks[2] = 0;
    uint32_t generation = generation_in(reverse ? RJ_ROLLBACK : RJ_PUBLISHING);
    if (board.poisoned) goto unknown;
    if (!generation || generation != board.admitted || (reverse != 0 && reverse != 1) || row >= board.rows) return RJ_REJECTED;
    if (!board.generation) {
        /* The manager freezes its placements under the whole-transport lease once publication starts. */
        if (reverse || !(s = mw_manager_journal_freeze(generation))) return RJ_REJECTED;
        board.generation = generation; /* even unknown: this generation now holds the manager */
        if (s != 1) goto poison;
    }
    if (board.work && (board.work != key || board.reverse != reverse)) {
        /* Only this row's rollback may overtake its forward work, once complete. */
        if (board.work != key || !reverse) goto poison;
        if (!board.complete && (s = mw_manager_journal_step(board.generation)) != 1) { if (!s) goto wait; goto poison; }
        board.work = board.ready = 0;
    }
    if (!board.work) {
        s = mw_manager_journal_stage(board.generation, r, reverse);
        if (!s && !reverse) return RJ_REJECTED; /* definite refusal, nothing changed */
        board.state[row] |= TOUCHED;
        if (s != 1) goto poison; /* a refused rollback cannot undo the forward work either */
        board.work = (uint8_t)key; board.reverse = (uint8_t)reverse; board.complete = board.ready = 0;
    }
    if (!board.complete) {
        s = mw_manager_journal_step(board.generation);
        if (!s) goto wait;
        if (s != 1) goto poison;
        board.complete = 1;
    }
    if ((!board.ready && !record(r, reverse, row)) || !same_view(&board.fact.row, r)) goto poison;
    masks[0] = masks[1] = masks[2] = board.fact.required;
    return RJ_READY;
poison:
    board.poisoned = 1;
unknown:
    masks[0] = masks[1] = 3;
    return RJ_UNKNOWN;
wait: /* cores stay unknown until the receipt: both possibly touched, none confirmed */
    masks[0] = masks[1] = 3;
    return RJ_WAIT;
}
int modwerk_machine_journal_commit_ready(const struct runtime_journal_view *r, int reverse, struct modwerk_journal_commit_fact *f)
{
    if (board.poisoned || !board.ready || !r || !f || board.fact.reverse != reverse ||
        board.fact.generation != generation_in(reverse ? RJ_ROLLBACK : RJ_PUBLISHING) || !same_view(&board.fact.row, r)) return 0;
    *f = board.fact;
    return 1;
}
int modwerk_machine_journal_commit_consume(const struct modwerk_journal_commit_fact *f)
{
    if (board.poisoned || !board.ready || !f || !same_view(&f->row, &board.fact.row) ||
        !same(&f->ticket, &board.fact.ticket, FACT_SCALARS)) return 0;
    uint8_t *state = &board.state[board.work - 1u];
    *state = (uint8_t)(f->reverse ? *state & ~PUBLISHED : *state | PUBLISHED);
    board.work = board.ready = 0;
    return 1;
}
/* Only a row this ledger never staged or published has a proof of no roots: it
 * was never dispatched, bound on a DSP or named by the catalogue. Touched rows
 * have no PC/register/stack/Part/UI proof and stay closed. */
int modwerk_machine_journal_roots_clear(const struct runtime_journal_view *r)
{
    uint32_t generation = generation_in(RJ_ROLLBACK);
    if (!r || !generation) return 0;
    if (board.generation != generation) return 1; /* never reached the manager: nothing staged or published */
    unsigned row = row_of(r->module);
    return !board.poisoned && row < board.rows && !board.state[row] && !board.work;
}
/* Keep (journal.h), answered from this ledger alone: the admitted rows in order,
 * each a fresh install whose forward receipt dsp.c consumed and never reversed,
 * nothing staged or stored. Retiring a predecessor needs a roots proof that does
 * not exist: refused, unchanged. Unknown manager work poisons. Consumed once;
 * the idle release follows. */
int mw_manager_journal_accept(uint32_t, const struct runtime_journal_view *, unsigned); /* dsp_journal_manager.h */
int modwerk_machine_journal_accept(const struct runtime_journal_view *rows, unsigned n)
{
    uint32_t generation = generation_in(RJ_TRIAL);
    if (board.poisoned) return -1;
    if (!generation || generation != board.admitted || generation != board.generation || !rows || !n || n != board.rows || board.work || board.ready) return 0;
    for (unsigned i = 0; i < n; ++i)
        if (rows[i].module != board.module[i] || board.state[i] != (TOUCHED | PUBLISHED) || rows[i].before.generation || !rows[i].after.generation) return 0;
    int s = mw_manager_journal_accept(generation, rows, n);
    if (s == 1) board.rows = 0;
    else if (s) board.poisoned = 1;
    return s == 1 ? 1 : s ? -1 : 0;
}
/* The manager releases its lease only for an idle journal. A refused release
 * keeps it, and with it every later generation closed, until reboot. */
void modwerk_machine_journal_idle(uint32_t generation)
{
    if (board.poisoned || !generation || board.generation != generation) return;
    int released = mw_manager_journal_release(generation);
    if (released == 1) board.generation = 0;
    else board.poisoned = released != 0;
}

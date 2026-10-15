/* SPDX-License-Identifier: GPL-3.0-or-later
 * Resident controller engines on demand, the ColdFire side (resident_engines.h). UI task only, under the stable
 * lock: relocation, region bookkeeping and owned jobs. The frame interrupt sees only ordinary owned packets with
 * no relocation list (each word is final before the WRITE is reserved). */
#include "resident_engines.h"
#include "transfer.h"

#ifdef MW_ENGINES_TEST
int mw_engines_test_quiet(void);
int mw_engines_test_settled(void);
#define QUIET() mw_engines_test_quiet()
#define SETTLED() mw_engines_test_settled()
#else
int modwerk_machine_stopped(void);
/* Stopped (no track or recorder running), and no pattern change queued (dsp.c's compaction reads the same bytes). */
#define QUIET() (modwerk_machine_stopped() && *(volatile uint8_t *)0x800065bfu == *(volatile uint8_t *)0x800065bdu && \
                 *(volatile uint8_t *)0x800065c0u == *(volatile uint8_t *)0x800065beu)
extern volatile uint32_t modwerk_runtime_ticks, modwerk_status_key_at; /* runtime.c, status.c: UI ticks (60 Hz), the last key */
int modwerk_dsp_moves_idle(void);                                       /* dsp.c: no self-test, rebind or waiting pick */
/* Live FX code may move for an engine (an evacuation, beside QUIET): two seconds after the last key or knob and no pick
 * waiting, as dsp.c's compaction waits. */
#define SETTLED() (modwerk_runtime_ticks - modwerk_status_key_at >= 120u && modwerk_dsp_moves_idle())
#endif

struct mw_engine mw_engines[2][3];
volatile uint32_t mw_engines_jobs, mw_engines_placed_count, mw_engines_unplaced_count, mw_engines_refused;
volatile uint8_t mw_engines_wait[2][3], mw_engines_admitted[3];
#ifdef MODWERK_DEV
struct mw_engines_view mw_engines_view = {.magic = {'M', 'W', 'E', 'V'}}; /* initialized: in .data, inside the dev MEM window */
#endif
enum { LANE_IDLE, LANE_WRITE, LANE_PLACE, LANE_UNPLACE };
static struct { struct dl_owned_job job; uint8_t op, k; } lane[2];
/* What each core's buffer holds: engine k + 1 relocated for table offset `offset` (0: nothing yet). A WRITE that
 * has to wait for the transport does not relocate again on every tick. */
static struct { uint16_t offset; uint8_t k; } buffered[2];
/* A job of ours failed or is uncertain on this core: the owned transport closed it for the boot (its fail-closed
 * rule), so nothing more is placed or unplaced there. Placed engines stay placed, free spans stay free. */
static uint8_t closed[2];

static unsigned index_of(unsigned feature) { return feature == 1u ? 0u : feature == 2u ? 1u : feature == 4u ? 2u : 3u; }
static unsigned arena(unsigned c) { return dl_pool_words[c] > DL_CODE_START ? dl_pool_words[c] - DL_CODE_START : 0u; }

void mw_engine_relocate(const struct mw_engine_unit *u, uint32_t base, uint32_t *out)
{
    for (unsigned i = 0; i < u->count; ++i)
        out[i] = (uint32_t)u->words[3u * i] << 16 | (uint32_t)u->words[3u * i + 1u] << 8 | u->words[3u * i + 2u];
    for (unsigned r = 0; r < u->relocation_count; ++r) {
        unsigned i = u->relocations[r] & 0x7fffu;
        out[i] = (u->relocations[r] & 0x8000u ? out[i] - base : out[i] + base) & 0xffffffu;
    }
}

/* The highest offset in core c's arena where n words meet no engine span but `skip`'s (top-down first fit, holes
 * reused). spans[k] < 0: none. -1: no room. */
static int spot(unsigned c, unsigned n, const int spans[3], unsigned skip)
{
    unsigned top = arena(c);
    if (!n || n > top) return -1;
    int at = (int)(top - n);
    for (unsigned moved = 1; moved;) {
        moved = 0;
        for (unsigned k = 0; k < 3u; ++k) {
            if (k == skip || spans[k] < 0) continue;
            int end = spans[k] + (int)mw_engine_units[c][k].count;
            if (at < end && at + (int)n > spans[k]) {
                at = spans[k] - (int)n;
                if (at < 0) return -1;
                moved = 1;
            }
        }
    }
    return at;
}
static void spans_of(unsigned c, int spans[3])
{
    for (unsigned k = 0; k < 3u; ++k) spans[k] = mw_engines[c][k].state == MW_ENGINE_FREE ? -1 : (int)mw_engines[c][k].offset;
}
/* What the region must reserve for these spans: from the lowest up to the arena's top. */
static unsigned reserve_of(unsigned c, const int spans[3])
{
    unsigned low = arena(c);
    for (unsigned k = 0; k < 3u; ++k) if (spans[k] >= 0 && (unsigned)spans[k] < low) low = (unsigned)spans[k];
    return arena(c) - low;
}
/* A span left the region: give the FX allocator back everything below the lowest engine still there. */
static void shrink(unsigned c)
{
    int spans[3];
    spans_of(c, spans);
    unsigned reserve = reserve_of(c, spans);
    if (reserve < dl_engine_reserved(c)) dl_engine_release(c, reserve);
}
static void free_span(unsigned c, unsigned k)
{
    mw_engines[c][k].state = MW_ENGINE_FREE, mw_engines[c][k].generation = 0;
    shrink(c);
}

void mw_engines_poll(void)
{
    for (unsigned c = 0; c < 2u; ++c) {
        if (lane[c].op == LANE_IDLE) continue;
        struct dl_owned_progress p;
        int s = dl_owned_job_poll(&lane[c].job, &p);
        if (!s) continue;
        int ok = s == 1 && p.sent_sequence == lane[c].job.last_sequence && p.acknowledged_sequence == lane[c].job.last_sequence;
        struct mw_engine *e = &mw_engines[c][lane[c].k];
        if (s == -2 || dl_owned_job_release(&lane[c].job) != 1) {
            /* Not this job's terminal state: nothing about the DSP is known, and the lane stays held for good. */
            dl_owned_fail_closed(c);
            e->state = MW_ENGINE_STUCK, closed[c] = 1;
            continue;
        }
        if (!ok) closed[c] = 1;
        unsigned op = lane[c].op;
        lane[c].op = LANE_IDLE;
        if (op == LANE_WRITE) {
            /* A failed WRITE sent no PLACE: the base word is still 0 and nothing reaches these words. */
            if (ok) e->state = MW_ENGINE_WRITTEN;
            else free_span(c, lane[c].k);
        } else if (op == LANE_PLACE) {
            if (ok) e->state = MW_ENGINE_PLACED, mw_engines_placed_count = mw_engines_placed_count + 1;
            else e->state = MW_ENGINE_STUCK; /* the base word may or may not name it: the span stays for this boot */
        } else if (ok) {
            free_span(c, lane[c].k);
            mw_engines_unplaced_count = mw_engines_unplaced_count + 1;
        } else e->state = MW_ENGINE_STUCK;
    }
}

int mw_engines_ready(unsigned feature, unsigned cores)
{
    unsigned k = index_of(feature);
    if (k > 2u || !cores || cores > 3u) return 0;
    for (unsigned c = 0; c < 2u; ++c)
        if ((cores >> c & 1u) && (!mw_engine_units[c][k].count || mw_engines[c][k].state != MW_ENGINE_PLACED)) return 0;
    return 1;
}

static int reserve(unsigned c, unsigned op, unsigned k, uint32_t generation)
{
    const struct mw_engine *e = &mw_engines[c][k];
    unsigned offset = DL_CODE_START + e->offset;
    int ok;
    if (op == LANE_WRITE) {
        const struct mw_engine_unit *u = &mw_engine_units[c][k];
        /* The buffer is free: one job per core, and the previous WRITE was released before this one. */
        if (buffered[c].k != k + 1u || buffered[c].offset != offset) {
            mw_engine_relocate(u, dl_pool_base[c] + offset, mw_engine_buffer[c]);
            buffered[c].k = (uint8_t)(k + 1u), buffered[c].offset = (uint16_t)offset;
        }
        struct dl_upload upload = {mw_engine_buffer[c], 0, u->count, 0, (uint16_t)offset};
        ok = dl_owned_upload_reserve(c, generation, &upload, &lane[c].job);
    } else ok = dl_owned_command_reserve(c, generation, 10u, 1u << k, op == LANE_PLACE ? offset : 0u, 1u, &lane[c].job);
    if (!ok) return 0;
    if (dl_owned_submit(&lane[c].job) != 1) {
        /* Reserved, not sent: give it back; if even that fails the core's owned channel is in doubt. */
        if (dl_owned_cancel(&lane[c].job) == 1) return 0;
        dl_owned_fail_closed(c);
        closed[c] = 1;
        return -1;
    }
    lane[c].op = (uint8_t)op, lane[c].k = (uint8_t)k;
    mw_engines_jobs = mw_engines_jobs + 1;
    return 1;
}

int mw_engines_place(unsigned feature, unsigned cores, uint32_t generation, const uint8_t busy[2])
{
    unsigned k = index_of(feature), placed = 1, stuck = 0;
    if (k > 2u || !cores || cores > 3u || !generation) return -1;
    for (unsigned c = 0; c < 2u; ++c) {
        if (!(cores >> c & 1u)) continue;
        struct mw_engine *e = &mw_engines[c][k];
        const struct mw_engine_unit *u = &mw_engine_units[c][k];
        volatile uint8_t *why = &mw_engines_wait[c][k];
        if (e->state == MW_ENGINE_PLACED) { *why = MW_WAIT_NONE; continue; }
        if (!u->count || e->state == MW_ENGINE_STUCK || closed[c]) { stuck = 1, *why = MW_WAIT_STUCK; continue; }
        placed = 0;
        /* One job per core; the board's own job, a playing sequencer or a queued pattern change defer the rest. */
        if (lane[c].op != LANE_IDLE) { *why = MW_WAIT_LANE; continue; }
        if (busy[c]) { *why = MW_WAIT_BOARD; continue; }
        if (e->state == MW_ENGINE_FREE) {
            int spans[3];
            spans_of(c, spans);
            int at = spot(c, u->count, spans, k);
            if (at < 0) { mw_engines_refused = mw_engines_refused + 1, *why = MW_WAIT_ROOM; continue; }
            spans[k] = at;
            unsigned need = reserve_of(c, spans);
            /* A claim the reserve already covers (an evacuation lowered the capacity for it) is bookkeeping only, taken
             * at once so the reserve never waits unowned; a new claim, and any code move, only while quiet. */
            if (need > dl_engine_reserved(c) && !QUIET()) { *why = MW_WAIT_PLAYING; continue; }
            int claim = dl_engine_claim(c, need, SETTLED() ? 2 : 1);
            if (claim <= 0) {
                if (claim < 0) mw_engines_refused = mw_engines_refused + 1;
                *why = claim < 0 ? MW_WAIT_CLAIM_REFUSED : dl_engine_why[c] >= 6u ? MW_WAIT_EVACUATION : MW_WAIT_CLAIM_BUSY;
                continue;
            }
            e->offset = (uint16_t)at, e->generation = generation, e->state = MW_ENGINE_CLAIMED;
        }
        if (!QUIET()) { *why = MW_WAIT_PLAYING; continue; }
        int r = e->state == MW_ENGINE_CLAIMED ? reserve(c, LANE_WRITE, k, generation) :
                e->state == MW_ENGINE_WRITTEN ? reserve(c, LANE_PLACE, k, generation) : 0;
        if (r > 0) e->state = e->state == MW_ENGINE_CLAIMED ? MW_ENGINE_WRITING : MW_ENGINE_PLACING, *why = MW_WAIT_NONE;
        else if (r < 0) e->state = MW_ENGINE_STUCK, stuck = 1, *why = MW_WAIT_STUCK;
        else *why = MW_WAIT_TRANSPORT;
    }
    return stuck ? -1 : (int)placed;
}

static int admit(unsigned feature, unsigned wanted);
int mw_engines_admit(unsigned feature, unsigned wanted)
{
    int verdict = admit(feature, wanted);
    unsigned k = index_of(feature);
    if (k < 3u) mw_engines_admitted[k] = (uint8_t)(verdict + 1);
    return verdict;
}
static int admit(unsigned feature, unsigned wanted)
{
    unsigned k = index_of(feature);
    if (k > 2u) return MW_ENGINE_STUCK_BOOT;
    for (unsigned c = 0; c < 2u; ++c)
        if (mw_engine_units[c][k].count && (mw_engines[c][k].state == MW_ENGINE_STUCK ||
                                            (closed[c] && mw_engines[c][k].state != MW_ENGINE_PLACED))) return MW_ENGINE_STUCK_BOOT;
    wanted |= feature;
    for (unsigned c = 0; c < 2u; ++c) {
        int spans[3];
        unsigned add = 0;
        spans_of(c, spans);
        for (unsigned j = 0; j < 3u; ++j) {
            if (!(wanted >> j & 1u) || !mw_engine_units[c][j].count || spans[j] >= 0) continue;
            int at = spot(c, mw_engine_units[c][j].count, spans, j);
            if (at < 0) return MW_ENGINE_MEMORY;
            spans[j] = at, add = 1;
        }
        if (add && dl_engine_claim(c, reserve_of(c, spans), 0) < 0) return MW_ENGINE_MEMORY;
    }
    return MW_ENGINE_FITS;
}

void mw_engines_collect(unsigned held, const uint8_t mask[2], unsigned known, const uint8_t busy[2])
{
    for (unsigned c = 0; c < 2u; ++c) {
        /* An evacuation lowers the capacity for the engine that asked; if that engine's feature is let go before it
         * claims, nothing frees its span: give the words back once no held feature's engine still waits here. */
        unsigned owed = 0;
        for (unsigned k = 0; k < 3u; ++k)
            owed |= (held >> k & 1u) && mw_engine_units[c][k].count && mw_engines[c][k].state == MW_ENGINE_FREE;
        if (!owed) shrink(c);
        for (unsigned k = 0; k < 3u; ++k) {
            struct mw_engine *e = &mw_engines[c][k];
            if ((held >> k & 1u) || lane[c].op != LANE_IDLE || busy[c] || closed[c] || !QUIET()) continue;
            if (e->state == MW_ENGINE_CLAIMED || e->state == MW_ENGINE_WRITTEN) free_span(c, k); /* never PLACEd */
            else if (e->state == MW_ENGINE_PLACED && (known >> c & 1u) && !(mask[c] >> k & 1u)) {
                int r = reserve(c, LANE_UNPLACE, k, e->generation);
                if (r) e->state = r > 0 ? MW_ENGINE_UNPLACING : MW_ENGINE_STUCK;
            }
        }
    }
}

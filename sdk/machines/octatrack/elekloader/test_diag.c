/* SPDX-License-Identifier: GPL-3.0-or-later
 * Host check of diag.c: a new log ignores earlier crashes, each start is counted and reports what crashed or stalled
 * since; five minutes of meters make one load record; the CPU at 90 % for a second makes one HOT incident with the
 * unit's context, at most one in ten minutes; five seconds without a UI tick while frames run make a FREEZE, added
 * with its length once the tick moves again, or with length 0 at the next start; LOG pages are 244 bytes. */
#include "diag.c"
#include <stdio.h>

static unsigned failures;
#define CHECK(x) do { if (!(x)) { failures++; fprintf(stderr, "%s:%d: %s\n", __FILE__, __LINE__, #x); } } while (0)
volatile struct diag_log modwerk_test_log;
volatile uint32_t modwerk_test_crash[4], modwerk_test_stall[3], modwerk_test_playing, modwerk_test_tempo24,
    modwerk_test_screen, modwerk_test_timer;
volatile uint8_t modwerk_test_running[16];
volatile uint32_t modwerk_status[5], modwerk_runtime_ticks, dl_frames;
void modwerk_track_machines(volatile uint8_t *out) { for (unsigned i = 0; i < 24u; ++i) out[i] = (uint8_t)(i + 1u); }

static volatile struct diag_incident *last(void) { return &LOG->incident[(LOG->incidents - 1u) % DIAG_INCIDENTS]; }
static void restart(void) { started = 0, ticks = 0, n = cpu_sum = cpu_peak = played = hot_run = hot_count = hot_at = 0; modwerk_diag_tick(); }
/* One UI tick, as the base runs it: runtime.c's count, then the subscribers. */
static void tick(void) { modwerk_runtime_ticks = modwerk_runtime_ticks + 1u; modwerk_diag_tick(); }

int main(void)
{
    modwerk_test_crash[0] = 0x4d574352u, modwerk_test_crash[1] = 2, modwerk_test_crash[3] = 0x40012345u;
    for (unsigned i = 0; i < sizeof modwerk_test_log; ++i) ((volatile uint8_t *)&modwerk_test_log)[i] = 0xa5;
    restart();
    CHECK(LOG->magic == DIAG_MAGIC && LOG->version == DIAG_VERSION && LOG->boot == 1u);
    CHECK(LOG->incidents == 1u && last()->kind == DIAG_START && last()->seq == 1u && last()->a == 2u << 16); /* old crashes: no CRASH */
    CHECK(LOG->loads == 0u && LOG->freeze_state == 0u);

    /* A crash and a stall since the last start. */
    modwerk_test_crash[1] = 3, modwerk_test_stall[0] = 0x4d575354u, modwerk_test_stall[1] = 1, modwerk_test_stall[2] = 2;
    restart();
    CHECK(LOG->boot == 2u && LOG->incidents == 4u);
    CHECK(LOG->incident[1].kind == DIAG_START && LOG->incident[2].kind == DIAG_CRASH && LOG->incident[2].a == 0x40012345u);
    CHECK(LOG->incident[3].kind == DIAG_STALL && LOG->incident[3].a == 2u && LOG->incident[3].fx[0] == 0 && LOG->incident[3].keys[0] == 0xffu);
    restart();
    CHECK(LOG->boot == 3u && LOG->incidents == 5u); /* nothing new crashed */

    /* Five minutes of meters: CPU 40 % then 60 %, playing half the time. */
    for (unsigned s = 0; s < WINDOW; ++s) {
        modwerk_status[0] = s < WINDOW / 2u ? 400u : 600u, modwerk_status[1] = 100u, modwerk_status[2] = 300u;
        modwerk_status[3] = 200u, modwerk_status[4] = 250u, modwerk_test_playing = s % 2u;
        for (unsigned t = 0; t < 30u; ++t) tick();
    }
    CHECK(LOG->loads == 1u && LOG->load[0].seq == LOG->seq && LOG->load[0].boot == 3u && LOG->load[0].minute == 5u);
    CHECK(LOG->load[0].cpu_mean == 500u && LOG->load[0].cpu_peak == 600u && LOG->load[0].dsp0_mean == 100u && LOG->load[0].dsp0_peak == 300u);
    CHECK(LOG->load[0].dsp1_mean == 200u && LOG->load[0].dsp1_peak == 250u && LOG->load[0].samples == WINDOW && LOG->load[0].playing == WINDOW / 2u);

    /* Not in the first minute after a start (the project load). */
    restart();
    modwerk_status[0] = 950u;
    unsigned at_start = LOG->incidents;
    for (unsigned t = 0; t < 3000u; ++t) tick();
    CHECK(LOG->incidents == at_start);
    modwerk_status[0] = 100u;
    for (unsigned t = 0; t < 4000u; ++t) tick();
    /* The CPU at 90 % for a second, with keys pressed before: one HOT with the context, then none for ten minutes. */
    for (int code = 0; code < 20; ++code) modwerk_diag_key(code, 1), modwerk_diag_key(code, 0);
    modwerk_test_running[0] = 33, modwerk_test_running[15] = 7, modwerk_test_screen = 0x400cbf2cu, modwerk_test_tempo24 = 120u * 24u, modwerk_test_playing = 1;
    modwerk_status[0] = 950u;
    unsigned before = LOG->incidents;
    for (unsigned t = 0; t < 60u; ++t) tick();
    CHECK(LOG->incidents == before + 1u && last()->kind == DIAG_HOT && last()->cpu == 950u && last()->a == 2u);
    CHECK(last()->fx[0] == 33u && last()->fx[15] == 7u && last()->screen == 0x400cbf2cu && last()->tempo24 == 2880u && last()->playing == 1u);
    CHECK(last()->machine[0] == 1u && last()->machine[23] == 24u && last()->keys[0] == 4u && last()->keys[15] == 19u);
    modwerk_status[0] = 100u;
    for (unsigned t = 0; t < 60u; ++t) tick();
    modwerk_status[0] = 950u;
    for (unsigned t = 0; t < 60u; ++t) tick();
    CHECK(LOG->incidents == before + 1u);

    /* The UI stands still for six seconds while frames run, then moves again. */
    modwerk_status[0] = 100u;
    before = LOG->incidents;
    for (unsigned f = 0; f < FREEZE_FRAMES + 2756u; ++f) modwerk_diag_frame();
    CHECK(LOG->freeze_state == 1u && LOG->freeze.kind == DIAG_FREEZE && LOG->freeze.boot == 4u && LOG->freeze.fx[0] == 33u);
    CHECK(LOG->incidents == before);
    tick(), modwerk_diag_frame(); /* the UI moves; the next frame sees it */
    CHECK(LOG->freeze_state == 2u && LOG->incidents == before);
    tick();
    CHECK(LOG->freeze_state == 0u && LOG->incidents == before + 1u && last()->kind == DIAG_FREEZE && last()->a == FREEZE_FRAMES + 2755u); /* the first frame only saw the tick move */
    CHECK(last()->seq == LOG->seq && last()->boot == 4u);

    /* Frozen until a power cycle: the next start adds it with length 0, under the session it happened in. */
    for (unsigned f = 0; f <= FREEZE_FRAMES; ++f) modwerk_diag_frame();
    CHECK(LOG->freeze_state == 1u);
    restart();
    CHECK(LOG->boot == 5u && LOG->freeze_state == 0u);
    CHECK(LOG->incident[(LOG->incidents - 2u) % DIAG_INCIDENTS].kind == DIAG_FREEZE && LOG->incident[(LOG->incidents - 2u) % DIAG_INCIDENTS].a == 0u);
    CHECK(LOG->incident[(LOG->incidents - 2u) % DIAG_INCIDENTS].boot == 4u && last()->kind == DIAG_START && last()->boot == 5u);

    /* Frames before the first tick of a start belong to nobody. */
    started = 0;
    for (unsigned f = 0; f < FREEZE_FRAMES + 1u; ++f) modwerk_diag_frame();
    CHECK(LOG->freeze_state == 0u);
    modwerk_diag_tick();

    /* The ring wraps: the newest 32 incidents, each with a seq above the last. */
    for (unsigned i = 0; i < 40u; ++i) restart();
    CHECK(LOG->incidents > DIAG_INCIDENTS && last()->seq == LOG->seq);
    for (unsigned i = 1; i < DIAG_INCIDENTS; ++i) {
        uint32_t a = LOG->incident[(LOG->incidents - 1u - i) % DIAG_INCIDENTS].seq, b = LOG->incident[(LOG->incidents - i) % DIAG_INCIDENTS].seq;
        CHECK(a < b);
    }

    /* LOG pages: 244 bytes each, the log byte for byte, then zeros. */
    uint8_t page[DIAG_PAGE];
    CHECK(modwerk_diag_read(page, 0) == DIAG_PAGE && page[0] == ((const uint8_t *)&modwerk_test_log)[0]);
    unsigned pages = (unsigned)((sizeof(struct diag_log) + DIAG_PAGE - 1u) / DIAG_PAGE);
    CHECK(modwerk_diag_read(page, pages - 1u) == DIAG_PAGE && page[DIAG_PAGE - 1u] == 0);
    CHECK(DIAG_PAGE % 64u != 0u);

    if (failures) fprintf(stderr, "%u failure(s)\n", failures);
    else puts("diag: start, crash and stall, load, HOT, freeze, restart and LOG pages passed");
    return failures != 0;
}

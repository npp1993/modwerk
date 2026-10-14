/* SPDX-License-Identifier: GPL-3.0-or-later
 * Appended to the real loader host suite (its synthetic adapter removed) and
 * saved_set_fixture.c, with real volatile_service.c and modset.c compiled
 * separately: the actual board adapter
 * journal_board.c over the actual journal and allocator. SYNTHETIC and only
 * test inputs: the manager-journal receipts and Keep answers, the reviewed association rows,
 * begin_safe, the map generation and a dsp.c-shaped single-use consumer. No
 * DSP ACK, source review, hardware or timing is established here. */
#define MW_JOURNAL_ASSOCIATION_STORAGE /* writable: synthetic rows get run-time digests */
#define MW_REVIEWED_JOURNAL_ASSOCIATIONS {{0},0,{0}}, {{0},0,{0}}, {{0},0,{0}},
#include "journal_board.c"
#include "volatile_service.h"

int modwerk_machine_journal_begin_safe(void) { CHECK(locked); return 1; } /* synthetic; ep0.c's gate has its own test */
uint32_t modwerk_fxmap_checked_generation(void) { return 5; }             /* synthetic map */
int modwerk_dsp_catalogue_handle(uint32_t module) { (void)module; return -1; }

/* Synthetic manager journal: dsp_journal_manager.h's phases as resident_journal.py checks them, no DSP. */
static int mgr_freeze = 1, mgr_stage = 1, mgr_step = 1, mgr_receipt = 1, mgr_release = 1, mgr_released = 1, mgr_ack;
static unsigned mgr_calls, mgr_stages, mgr_releases;
static uint32_t mgr_ticket = 100, mgr_replay;
static uint8_t mgr_required = 3;
static void manager_call(uint32_t generation) { CHECK(locked && generation && generation == journal.progress.generation); ++mgr_calls; }
int mw_manager_journal_freeze(uint32_t g) { manager_call(g); CHECK(journal.progress.phase == RJ_PUBLISHING); return mgr_freeze; }
int mw_manager_journal_stage(uint32_t g, const struct runtime_journal_view *r, int reverse)
{ manager_call(g); CHECK(r && journal.progress.phase == (reverse ? RJ_ROLLBACK : RJ_PUBLISHING)); ++mgr_stages; return mgr_stage; }
int mw_manager_journal_step(uint32_t g) { manager_call(g); return mgr_step; }
int mw_manager_journal_receipt(uint32_t g, const struct runtime_journal_view *r, int reverse, uint8_t *required, struct mw_manager_core_receipt out[2])
{
    manager_call(g); CHECK(r && (reverse == 0 || reverse == 1)); *required = mgr_required;
    for (unsigned c = 0; c < 2; ++c) if (mgr_required >> c & 1u)
        out[c] = (struct mw_manager_core_receipt){mgr_replay ? mgr_replay : ++mgr_ticket, 9, 0, 0, 1, 4, (uint16_t)(4 + mgr_ack), 0, 0, (uint8_t)mgr_released};
    return mgr_receipt;
}
int mw_manager_journal_release(uint32_t g) { manager_call(g); CHECK(journal.progress.phase == RJ_IDLE); ++mgr_releases; return mgr_release; }
static int mgr_accept = 1;
static unsigned mgr_accepts;
int mw_manager_journal_accept(uint32_t g, const struct runtime_journal_view *rows, unsigned n)
{
    manager_call(g); CHECK(journal.progress.phase == RJ_TRIAL && rows && n == journal.progress.records);
    for (unsigned i = 0; rows && i < n; ++i) CHECK(!rows[i].before.generation && rows[i].after.generation);
    ++mgr_accepts; return mgr_accept;
}

/* dsp.c-shaped consumer: preflight reads the fact, commit rereads and consumes once. */
static struct modwerk_journal_commit_fact preflight, last_fact;
static int preflighted, replay_after_first;
static unsigned commits;
int modwerk_machine_journal_switch_safe(const struct runtime_journal_view *r, int reverse)
{
    struct modwerk_journal_commit_fact f;
    struct runtime_journal_view wrong = *r;
    CHECK(locked && !masked); preflighted = 0;
    wrong.after.generation ^= 1; CHECK(!modwerk_machine_journal_commit_ready(&wrong, reverse, &f));
    wrong = *r; wrong.before.owned_extent ^= 16; CHECK(!modwerk_machine_journal_commit_ready(&wrong, reverse, &f));
    wrong = *r; wrong.package_sha256[31] ^= 1; CHECK(!modwerk_machine_journal_commit_ready(&wrong, reverse, &f));
    CHECK(!modwerk_machine_journal_commit_ready(r, !reverse, &f));
    ++journal.progress.generation; CHECK(!modwerk_machine_journal_commit_ready(r, reverse, &f)); --journal.progress.generation;
    if (modwerk_machine_journal_commit_ready(r, reverse, &preflight) != 1) return 0;
    CHECK(preflight.generation == journal.progress.generation && preflight.map_generation == 5 && preflight.reverse == reverse);
    CHECK(preflight.required == journal.progress.required && preflight.released == preflight.required &&
          preflight.confirmed == journal.progress.confirmed && preflight.catalogue_handle == 255);
    f = preflight; ++f.ticket; CHECK(!modwerk_machine_journal_commit_consume(&f));
    f = preflight; f.released ^= 1; CHECK(!modwerk_machine_journal_commit_consume(&f));
    f = preflight; f.row.position ^= 1; CHECK(!modwerk_machine_journal_commit_consume(&f));
    f = preflight; f.map_generation++; CHECK(!modwerk_machine_journal_commit_consume(&f));
    preflighted = 1;
    return 1;
}
int modwerk_machine_journal_committed(const struct runtime_journal_view *r, int reverse)
{
    struct modwerk_journal_commit_fact f;
    int had = preflighted;
    CHECK(locked && !masked); preflighted = 0;
    if (!had || modwerk_machine_journal_commit_ready(r, reverse, &f) != 1 || f.ticket != preflight.ticket ||
        modwerk_machine_journal_commit_consume(&f) != 1) return 0;
    CHECK(!modwerk_machine_journal_commit_consume(&f) && !modwerk_machine_journal_commit_ready(r, reverse, &f)); /* single use */
    if (commits++ == 0 && replay_after_first) mgr_replay = f.job_ticket[0];
    last_fact = f;
    return 1;
}

static struct mvs_service svc;
static uint8_t stage[16384], base[32] = {1}, session[32] = {2}, whole[4096], baseline_digest[32], offer_digest[32], record_digest[2][32];
static uint32_t whole_bytes, seq = 1;
/* first 111 replaces the live 111; 110 and 109 are fresh installs beside 113. */
static void make_bundle_from(uint32_t first)
{
    memset(whole, 0, sizeof whole); memcpy(whole, "MWBT", 4);
    whole[5] = whole[7] = 1; whole[9] = 88; whole[11] = whole[13] = 2;
    memcpy(whole + 24, base, 32); memcpy(whole + 56, baseline_digest, 32);
    put32(whole + 88, first); put32(whole + 92, 113); uint32_t at = 96;
    for (unsigned i = 0; i < 2; ++i) {
        id = i ? 113 : first; begin(64, 0, 0, 0, 0, 1, (uint8_t)(0x51 + i));
        site(STOCK + (i ? 96 : first == 111 ? 32 : first == 110 ? 128 : 160), 6);
        put32(whole + at, id); put32(whole + at + 4, n); mu_sha256(p, n, record_digest[i]); memcpy(whole + at + 8, record_digest[i], 32);
        put32(whole + at + 40, 1u << i); at += 48; memcpy(whole + at, p, n); at += (n + 3u) & ~3u;
    }
    whole_bytes = at; put32(whole + 16, at); mu_sha256(whole, at, offer_digest);
}
static void make_bundle(void) { make_bundle_from(111); }
static void declare(unsigned row, unsigned record, uint32_t module, uint32_t extra)
{ memcpy(associations[row].package_sha256, record_digest[record], 32); associations[row].module = module; associations[row].participants[0] = module; associations[row].participants[1] = extra; }
static int send(unsigned command, uint32_t now)
{
    uint8_t f[4096] = {0}; uint32_t length = 0;
    memcpy(f, "MWVB", 4); f[4] = 1; f[5] = (uint8_t)command;
    if (command == 1) { memcpy(f + 96, baseline_digest, 32); memcpy(f + 128, offer_digest, 32); put32(f + 160, whole_bytes); length = 72; }
    if (command == 2) { put32(f + 96, 0); memcpy(f + 100, whole, whole_bytes); length = whole_bytes + 4; }
    put32(f + 8, seq++); put32(f + 12, command == 1 ? 0 : svc.transaction); put32(f + 16, command == 1 ? 0 : svc.generation);
    put32(f + 20, length); memcpy(f + 24, base, 32); memcpy(f + 56, session, 32);
    int accepted = modwerk_volatile_queue(&svc, f, 96 + length);
    if (accepted) modwerk_volatile_service(&svc, now);
    return accepted;
}
static void verify(uint32_t now)
{
    CHECK(send(1, now) && svc.phase == MVS_RECEIVING && svc.result == MVS_OK);
    CHECK(send(2, now) && svc.received == whole_bytes && send(3, now));
    for (unsigned i = 0; i < 4 && svc.verifying; ++i) modwerk_volatile_service(&svc, now);
}
static void service_for(uint32_t now) { for (unsigned i = 0; i < 8; ++i) modwerk_volatile_service(&svc, now); }

int main(int argc, char **argv)
{
    if (legacy_main()) return 1;
    CHECK(argc == 2);
    id = 111; begin(32, 0, 0, 0, 0, 1, 0x11); site(STOCK + 32, 6);
    CHECK(b->enter(0) && b->prepare(0, p, n) && b->publish(0) == MU_APPLIED && b->retire(0) && b->leave(0));
    id = 112; begin(32, 0, 0, 0, 0, 1, 0x12); site(STOCK + 64, 6);
    CHECK(b->enter(0) && b->prepare(0, p, n) && b->publish(0) == MU_APPLIED && b->retire(0) && b->leave(0));
    seed_saved_set();
    const struct runtime_module *before0 = live[0], *before1 = live[1];
    uint32_t lock = modwerk_machine_lock(); CHECK(modwerk_runtime_journal_digest(baseline_digest)); modwerk_machine_unlock(lock);
    CHECK(modwerk_volatile_init(&svc, stage, sizeof stage, base, session));
    make_bundle();
    uint32_t free_before = modwerk_runtime_free(0); uint8_t stock_before[sizeof stock]; memcpy(stock_before, stock, sizeof stock);
    const char *c = argv[1];
    if (!MODWERK_JOURNAL_BOARD_ENABLED) {
        /* Public default: nothing opens, whatever the tables and providers say. */
        declare(0, 0, 111, 0); declare(1, 1, 113, 0);
        CHECK(!strcmp(c, "closed") && svc.result == MVS_UNSUPPORTED && !(svc.status[7] & 8));
        CHECK(send(1, 100) && svc.phase == MVS_IDLE && svc.result == MVS_UNSUPPORTED && !svc.transaction);
        CHECK(modwerk_runtime_journal_begin() == RJ_REFUSED && !modwerk_runtime_volatile_busy() && !mgr_calls);
    } else if (!strcmp(c, "association")) {
        /* Missing, partial, mismatched or duplicated declarations refuse before allocation or a manager call. */
        for (unsigned k = 0; k < 4; ++k) {
            memset(associations, 0, sizeof associations);
            if (k) declare(0, 0, 111, 0);
            if (k == 2) declare(1, 1, 113, 114);
            if (k == 3) { declare(1, 1, 113, 0); declare(2, 0, 111, 0); }
            verify(100 + k);
            CHECK(svc.result == MVS_REFUSED && svc.phase == MVS_RECEIVING && !journal.progress.records && modwerk_runtime_free(0) == free_before);
            CHECK(send(7, 100 + k) && svc.phase == MVS_IDLE && !mgr_calls);
        }
        CHECK(!modwerk_machine_journal_association(111, record_digest[0], (const uint32_t[]){111}, 1));
        memset(associations, 0, sizeof associations); declare(0, 0, 111, 0);
        CHECK(modwerk_machine_journal_association(111, record_digest[0], (const uint32_t[]){111}, 1));
        CHECK(!modwerk_machine_journal_association(111, record_digest[0], (const uint32_t[]){111, 113}, 2));
        CHECK(!modwerk_machine_journal_association(113, record_digest[0], (const uint32_t[]){113}, 1));
    } else {
        declare(0, 0, 111, 0); declare(1, 1, 113, 0);
        if (!strcmp(c, "freeze") || !strcmp(c, "idle")) {
            /* Refused freeze or first stage: nothing staged, rollback is clear; only a frozen lease is released. */
            int idle = !strcmp(c, "idle");
            if (idle) mgr_stage = 0, mgr_release = 0; else mgr_freeze = 0;
            verify(100); CHECK(svc.phase == MVS_VERIFIED && !mgr_calls);
            CHECK(send(4, 101)); service_for(101);
            CHECK(svc.phase == MVS_IDLE && !memcmp(svc.current, baseline_digest, 32) && modwerk_runtime_free(0) == free_before);
            CHECK(mgr_calls == (idle ? 3u : 1u) && mgr_releases == (unsigned)idle && !commits && !board.poisoned);
            CHECK(board.generation == (idle ? journal.progress.generation : 0u)); /* a refused release keeps the lease */
            if (idle) {
                verify(102); CHECK(svc.result == MVS_REFUSED && send(7, 103) && svc.phase == MVS_IDLE && mgr_calls == 3);
            } else {
                mgr_freeze = -1; verify(102); CHECK(send(4, 103)); service_for(103);
                CHECK(svc.phase == MVS_QUARANTINE && board.poisoned && mgr_calls == 2);
                CHECK(send(6, 104)); service_for(104); /* unknown freeze: held, never retried */
                CHECK(svc.phase == MVS_QUARANTINE && mgr_calls == 2 && reachable(journal.row[1].after));
            }
        } else if (!strncmp(c, "keep", 4)) {
            /* Keep from this ledger: fresh installs only, consumed once, then the idle release. */
            const char *k = c + 4; int replace = !strcmp(k, "replace");
            memset(associations, 0, sizeof associations); make_bundle_from(replace ? 111 : 110);
            declare(0, 0, replace ? 111 : 110, 0); declare(1, 1, 113, 0);
            mgr_required = 0; /* synthetic positively checked no-job receipts, as for unplaced installs */
            verify(100); CHECK(svc.phase == MVS_VERIFIED && send(4, 101)); service_for(102);
            CHECK(svc.phase == MVS_STOPPED_TRIAL && commits == 2 && journal.progress.published == 2 && board.rows == 2);
            uint8_t trial[32]; memcpy(trial, svc.current, 32);
            if (replace) {
                /* Retiring a predecessor has no roots proof: refused before the manager, nothing changed. */
                CHECK(send(9, 103) && svc.result == MVS_REFUSED && svc.phase == MVS_STOPPED_TRIAL && !mgr_accepts);
                CHECK(board.rows == 2 && board.state[0] == (TOUCHED | PUBLISHED) && board.generation && !mgr_releases);
                CHECK(send(6, 104)); service_for(104); /* reverse still works before Keep; roots stay unproven */
                CHECK(commits == 4 && live[0] == before0 && svc.phase == MVS_ROLLBACK && !mgr_releases && !board.poisoned);
            } else if (!strcmp(k, "unknown")) {
                mgr_accept = -1;
                CHECK(send(9, 103) && svc.phase == MVS_QUARANTINE && board.poisoned && mgr_accepts == 1);
                CHECK(journal.progress.phase == RJ_QUARANTINE && board.generation && !mgr_releases);
                unsigned calls = mgr_calls;
                CHECK(send(6, 104)); service_for(104); modwerk_volatile_tick(&svc, 9000); service_for(9000);
                CHECK(svc.phase == MVS_QUARANTINE && mgr_calls == calls && !mgr_releases && reachable(journal.row[0].after));
            } else {
                CHECK(!*k);
                mgr_accept = 0; CHECK(send(9, 103) && svc.result == MVS_REFUSED && svc.phase == MVS_STOPPED_TRIAL);
                CHECK(mgr_accepts == 1 && board.rows == 2 && !board.poisoned && journal.progress.phase == RJ_TRIAL);
                mgr_accept = 1; CHECK(send(9, 104) && svc.phase == MVS_IDLE && svc.result == MVS_OK && mgr_accepts == 2);
                CHECK(mgr_releases == 1 && !board.generation && !board.rows && !board.poisoned && !modwerk_runtime_volatile_busy());
                CHECK(!memcmp(svc.baseline, trial, 32) && !memcmp(svc.current, trial, 32) && live[2] && live[3]);
                CHECK(send(9, 105) && svc.result == MVS_STALE && mgr_accepts == 2 && mgr_releases == 1);
                CHECK(modwerk_modset_count == 4 && modwerk_modset_unsaved() == 1u); /* the saved set, until the engine writes it */
                /* The lease is released: the legacy path and the next generation's admission are open. */
                CHECK(b->enter(0) && b->leave(0));
                memcpy(baseline_digest, trial, 32); make_bundle_from(109);
                memset(associations, 0, sizeof associations); declare(0, 0, 109, 0); declare(1, 1, 113, 0);
                verify(106); CHECK(svc.phase == MVS_VERIFIED && board.admitted == journal.progress.generation);
                CHECK(send(7, 107)); service_for(107); CHECK(svc.phase == MVS_IDLE && !memcmp(svc.current, trial, 32));
            }
        } else if (!strcmp(c, "abort")) {
            verify(100); CHECK(svc.phase == MVS_VERIFIED && journal.progress.records == 2 && board.admitted == journal.progress.generation);
            CHECK(send(7, 101)); service_for(101);
            CHECK(svc.phase == MVS_IDLE && svc.result == MVS_OK && !memcmp(svc.current, baseline_digest, 32));
            CHECK(!mgr_calls && !board.generation && !commits && modwerk_runtime_free(0) == free_before);
        } else {
            verify(100); CHECK(svc.phase == MVS_VERIFIED);
            mgr_step = 0; CHECK(send(4, 101) && svc.phase == MVS_PUBLISHING);
            CHECK(mgr_stages == 1 && board.generation == journal.progress.generation && !journal.progress.published);
            CHECK(svc.status[192] == 3 && svc.status[193] == 3 && !svc.status[194]);
            if (!strcmp(c, "publish")) {
                mgr_step = 1; service_for(102);
                CHECK(svc.phase == MVS_STOPPED_TRIAL && journal.progress.published == 2 && commits == 2 && memcmp(svc.current, baseline_digest, 32));
                CHECK(live[0] != before0 && reachable(before0) && memcmp(stock, stock_before, sizeof stock));
                CHECK(send(5, 103) && svc.result == MVS_REFUSED && svc.phase == MVS_STOPPED_TRIAL); /* no latch to release */
                struct runtime_owner after0; CHECK(modwerk_runtime_owner_snapshot(live[0]->dsp.image, &after0));
                CHECK(send(6, 104)); service_for(104);
                /* Both exact reverse receipts commit; roots stay unproven, so both generations stay held. */
                CHECK(commits == 4 && last_fact.reverse && !last_fact.catalogue_target && mgr_stages == 4);
                CHECK(live[0] == before0 && live[1] == before1 && !memcmp(stock, stock_before, sizeof stock));
                CHECK(svc.phase == MVS_ROLLBACK && journal.progress.phase == RJ_ROLLBACK && !journal.progress.published);
                CHECK(modwerk_runtime_owner_valid(&after0) && !mgr_releases && !board.poisoned && modwerk_runtime_free(0) < free_before);
            } else if (!strcmp(c, "unpublished")) {
                /* Rollback overtakes forward work only once it completes; the target already lives. */
                CHECK(send(6, 102) && svc.phase == MVS_ROLLBACK); service_for(102);
                CHECK(mgr_stages == 1 && !commits && svc.phase == MVS_ROLLBACK);
                mgr_step = 1; service_for(103);
                CHECK(mgr_stages == 2 && commits == 1 && last_fact.reverse && last_fact.catalogue_target);
                CHECK(live[0] == before0 && !memcmp(stock, stock_before, sizeof stock) && svc.phase == MVS_ROLLBACK && !mgr_releases);
            } else {
                /* Unknown or malformed manager work: quarantine, hold both, never call the manager again. */
                if (!strcmp(c, "unknown")) mgr_step = -1;
                else if (!strcmp(c, "released")) mgr_step = 1, mgr_released = 0;
                else if (!strcmp(c, "acknowledged")) mgr_step = 1, mgr_ack = 1;
                else { CHECK(!strcmp(c, "replay")); mgr_step = 1; replay_after_first = 1; }
                service_for(102);
                CHECK(svc.phase == MVS_QUARANTINE && journal.progress.phase == RJ_QUARANTINE && board.poisoned);
                CHECK(commits == (unsigned)!strcmp(c, "replay") && journal.progress.published == (uint16_t)commits);
                unsigned calls = mgr_calls; uint32_t held = modwerk_runtime_free(0);
                CHECK(send(6, 103)); service_for(103); modwerk_volatile_tick(&svc, 9000); service_for(9000);
                CHECK(svc.phase == MVS_QUARANTINE && mgr_calls == calls && modwerk_runtime_free(0) == held && !mgr_releases);
                CHECK(reachable(before0) && reachable(journal.row[0].after) && reachable(journal.row[1].after));
                struct modwerk_journal_commit_fact f; struct runtime_journal_view v;
                CHECK(journal_view(&journal.row[0], &v) && !modwerk_machine_journal_commit_ready(&v, 1, &f));
            }
        }
    }
    uint8_t capabilities[12]; modwerk_runtime_capabilities(capabilities); CHECK(!(be16(capabilities + 6) & 64u));
    CHECK(!locked && !masked && !modwerk_machine_journal_trial(1));
    if (failures) { fprintf(stderr, "%u journal board checks failed\n", failures); return 1; }
    return 0;
}

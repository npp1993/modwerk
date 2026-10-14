# SPDX-License-Identifier: GPL-3.0-or-later
"""Private base's initialized-zero DSP loader storage, without a code-size policy.

Call unit() on manager.c, transfer.c and selection.c after every other
substitution, passing the preserved upstream source as reference. Only the
listed all-zero declarations lose their initializer and move to ordinary .bss;
the core's uncached boot clear zeroes them in the same boot routine that copies
.data, before core_up. The same O2 code, capacities and every nonzero
initializer stay. build_core.check_zero_state proves from the final link that
each listed object is inside the cleared BSS and outside the retained skip.
"""
import hashlib


# unit -> (sha256 of the preserved upstream source, ((declaration, without its zero initializers, objects), ...))
UNITS = {
    'manager.c': ('2098f13e8a2217675b927c7b55feca45d1503966a1ae5ebe16de0701d75d19aa', (
        ('static struct dl_allocator allocator={0};', 'static struct dl_allocator allocator;', ('allocator',)),
        ('static struct dl_buffers buffers={0};', 'static struct dl_buffers buffers;', ('buffers',)),
        ('static uint8_t desired[16]={0};', 'static uint8_t desired[16];', ('desired',)),
        ('static uint8_t observed[16]={0};', 'static uint8_t observed[16];', ('observed',)),
        ('static unsigned observed_valid=0;', 'static unsigned observed_valid;', ('observed_valid',)),
        ('static unsigned initialized=0,phase=0,cursor=0,waiting=0,automatic=0,cancelling=0;',
         'static unsigned initialized,phase,cursor,waiting,automatic,cancelling;',
         ('initialized', 'phase', 'cursor', 'waiting', 'automatic', 'cancelling')),
        ('static uint32_t current=0;', 'static uint32_t current;', ('current',)),
        ('static int result=0;', 'static int result;', ('result',)),
        ('volatile uint32_t dl_residency_commits=0,dl_residency_rollbacks=0,dl_residency_failures=0;',
         'volatile uint32_t dl_residency_commits,dl_residency_rollbacks,dl_residency_failures;',
         ('dl_residency_commits', 'dl_residency_rollbacks', 'dl_residency_failures')),
        ('volatile uint32_t dl_residency_words[2]={0};', 'volatile uint32_t dl_residency_words[2];', ('dl_residency_words',)),
        ('volatile uint32_t dl_unguarded=0;', 'volatile uint32_t dl_unguarded;', ('dl_unguarded',)),
        ('static uint8_t queued_ids[16]={0};', 'static uint8_t queued_ids[16];', ('queued_ids',)),
        ('static uint32_t queued_token=0;', 'static uint32_t queued_token;', ('queued_token',)),
        ('static uint8_t owed_id[16]={0};', 'static uint8_t owed_id[16];', ('owed_id',)),
        ('static uint32_t parked=0;', 'static uint32_t parked;', ('parked',)),
        ('static uint8_t unsafe[16]={0};', 'static uint8_t unsafe[16];', ('unsafe',)),
        ('static unsigned unsafe_valid=0;', 'static unsigned unsafe_valid;', ('unsafe_valid',)))),
    # The eDMA packets keep their 16-byte alignment; transfer.c reaches them only through the uncached alias.
    'transfer.c': ('523090ed337d5f1677c25b7968dd237a4f60f4ae2df98888b6c78d77eb8814f4', (
        ('volatile uint16_t dl_tx[2][DL_WORDS] __attribute__((aligned(16)))={{0}}, dl_rx[2][32] __attribute__((aligned(16)))={{0}};',
         'volatile uint16_t dl_tx[2][DL_WORDS] __attribute__((aligned(16))), dl_rx[2][32] __attribute__((aligned(16)));',
         ('dl_tx', 'dl_rx')),
        ('volatile uint32_t dl_frames=0, dl_accepted[2]={0}, dl_rejected[2]={0}, dl_errors=0;',
         'volatile uint32_t dl_frames, dl_accepted[2], dl_rejected[2], dl_errors;',
         ('dl_frames', 'dl_accepted', 'dl_rejected', 'dl_errors')),
        ('volatile uint32_t dl_storm=0, dl_storm_sent=0;', 'volatile uint32_t dl_storm, dl_storm_sent;',
         ('dl_storm', 'dl_storm_sent')),
        ('volatile uint32_t dl_request_probe=0, dl_request_stage=0, dl_modal_pending=0, dl_modal_shown=0;',
         'volatile uint32_t dl_request_probe, dl_request_stage, dl_modal_pending, dl_modal_shown;',
         ('dl_request_probe', 'dl_request_stage', 'dl_modal_pending', 'dl_modal_shown')),
        ('static uint16_t sequence[2]={0}, pending[2]={0}, age[2]={0};', 'static uint16_t sequence[2], pending[2], age[2];',
         ('sequence', 'pending', 'age')),
        ('static uint32_t requests=0, stages=0;', 'static uint32_t requests, stages;', ('requests', 'stages')),
        ('static unsigned flags_sent[2]={0,0};', 'static unsigned flags_sent[2];', ('flags_sent',)),
        ('static struct job jobs[2]={0};', 'static struct job jobs[2];', ('jobs',)),
        ('volatile uint32_t dl_frame_gap=0;', 'volatile uint32_t dl_frame_gap;', ('dl_frame_gap',)),
        ('static uint32_t frame_at=0;', 'static uint32_t frame_at;', ('frame_at',)))),
    'selection.c': ('4dae3a407debcc0eff9a89f3bc0194a3807bde9d28d68084db5633a5e5d73866', (
        ('volatile uint32_t dl_selection_requested=0, dl_selection_completed=0;',
         'volatile uint32_t dl_selection_requested, dl_selection_completed;',
         ('dl_selection_requested', 'dl_selection_completed')),
        ('volatile uint32_t dl_selection_cancelled=0, dl_selection_refused=0;',
         'volatile uint32_t dl_selection_cancelled, dl_selection_refused;',
         ('dl_selection_cancelled', 'dl_selection_refused')),
        ('static struct dl_selection queued={0};', 'static struct dl_selection queued;', ('queued',)),
        ('static uint32_t serial=0, token=0, applying=0;', 'static uint32_t serial, token, applying;',
         ('serial', 'token', 'applying')),
        ('static unsigned pending=0, replay=0;', 'static unsigned pending, replay;', ('pending', 'replay')),
        ('static uint32_t later=0, later_bank=0, later_part=0;', 'static uint32_t later, later_bank, later_part;',
         ('later', 'later_bank', 'later_part')),
        ('volatile uint32_t dl_selection_queued=0;', 'volatile uint32_t dl_selection_queued;', ('dl_selection_queued',)))),
}
MOVED = {name: tuple(o for _, _, objects in seams for o in objects) for name, (_, seams) in UNITS.items()}


def unit(name, text, reference):
    """Fail closed if the exact reviewed upstream source or any zero seam changed."""
    pinned, seams = UNITS[name]
    if (not isinstance(text, str) or not isinstance(reference, str) or
            hashlib.sha256(reference.encode()).hexdigest() != pinned):
        raise ValueError('%s zero-state source changed; review the private BSS port.' % name)
    for old, new, _ in seams:
        if text.count(old) != 1:
            raise ValueError('%s zero-state declaration changed; review the private BSS port.' % name)
        text = text.replace(old, new)
    return text

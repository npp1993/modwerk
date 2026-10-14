# SPDX-License-Identifier: GPL-3.0-or-later
"""Exact generated-source gates for the private fixed-file export lease.

Preserved Octabam and canonical DSP sources stay unchanged. This transform is
applied only after their reviewed base and optional resident substitutions.
"""

def _change(text, old, new):
    if text.count(old) != 1:
        raise ValueError('Saved-set export source seam changed: ' + old[:64])
    return text.replace(old, new)

def dsp(text):
    if 'modwerk_dsp_export_idle' in text:
        raise ValueError('Saved-set export source seam changed: DSP already wired')
    text = 'int modwerk_saved_set_busy(void);\n' + text
    for signature in ('int modwerk_dsp_probe(unsigned core)\n{',
                      'int modwerk_dsp_meter_read(unsigned core, unsigned first, unsigned words)\n{',
                      'int modwerk_dsp_pick(unsigned slot, unsigned track, unsigned row)\n{',
                      'int modwerk_selftest_start(void)\n{'):
        text = _change(text, signature, signature + '\n    if (modwerk_saved_set_busy()) return 0;')
    text = _change(text, 'void modwerk_dsp_tick(void)\n{',
                   'void modwerk_dsp_tick(void)\n{\n    if (modwerk_saved_set_busy()) return;')
    return text + '''
/* Fixed counter/job reads only: no pool scan, DSP probe or work scheduling. */
int modwerk_dsp_export_idle(void)
{
#ifndef MODWERK_HOST
    int dl_transfer_export_idle(void), dl_selection_export_idle(void);
#ifdef MODWERK_DSP_XWATCH
    if (xwatch_wanted >= 0) return 0;
#endif
    return dl_publication_idle() && dl_transfer_export_idle() && dl_selection_export_idle() &&
           !dl_phase && !dl_c1_phase && !rebinding && !moving_count && !nudge &&
           probing < 0 && peeking < 0 && meter_wanted < 0 &&
           modwerk_selftest.state != SELFTEST_RUNNING && !modwerk_dsp_compact_step && picks_in == picks_out;
#else
    return 0; /* Board safety is never inferred from a host stub. */
#endif
}
'''

def transfer(text, resident=False):
    if 'dl_transfer_export_idle' in text:
        raise ValueError('Saved-set export source seam changed: transfer already wired')
    text = 'int modwerk_saved_set_busy(void);\n' + text
    signatures = ['int dl_upload_start(unsigned c,const struct dl_upload *u) {',
                  'int dl_command_start(unsigned c,unsigned op,unsigned id,unsigned init,unsigned proc) {',
                  'int dl_sum_start(unsigned c,unsigned offset,unsigned count,uint32_t expected) {']
    if resident:
        signatures.append('int dl_hook_reset_start(unsigned c,unsigned feature,unsigned offset,unsigned count,const uint32_t *words) {')
    for signature in signatures:
        text = _change(text, signature, signature + '\n    if(modwerk_saved_set_busy()) return 0;')
    text = _change(text, '    ++dl_frames;',
                   '    ++dl_frames;\n    if(modwerk_saved_set_busy()) return 0;')
    text = _change(text, 'void dl_ui(void) {', 'void dl_ui(void) {\n    if(modwerk_saved_set_busy()) return;')
    return text + '''
int dl_transfer_export_idle(void) {
    return !pending[0] && !pending[1] && !jobs[0].state && !jobs[1].state &&
           dl_request_probe==requests && dl_request_stage==stages;
}
'''

def selection(text):
    if 'dl_selection_export_idle' in text:
        raise ValueError('Saved-set export source seam changed: selection already wired')
    text = 'int modwerk_saved_set_busy(void);\n' + text
    text = _change(text, 'static unsigned guard(unsigned slot,unsigned row,uintptr_t source) {',
                   'static unsigned guard(unsigned slot,unsigned row,uintptr_t source) {\n    if(modwerk_saved_set_busy()) return 0;')
    return text + '''
int dl_selection_export_idle(void) { return !pending && !replay && !applying && !later; }
'''

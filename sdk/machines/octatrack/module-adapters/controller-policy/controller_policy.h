/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef MODWERK_CONTROLLER_POLICY_H
#define MODWERK_CONTROLLER_POLICY_H

struct mw_hook_buffer_claim;

/* Strong board boundary, never an uploaded policy or caller-ready override.
 * Populated policy needs exact source/package identity and owned generations.
 * A buffer policy entry is an exact, reviewed claim that narrows an effect's
 * whole-block default (dsp.c modwerk_dsp_buffer_permitted) or proves a head
 * shadow; 0 means none, and the whole block is claimed. This bridge has none. */
int modwerk_stock_hook_buffer_policy(unsigned core, unsigned id,
                                    struct mw_hook_buffer_claim *out);
int modwerk_stock_hook_fixed_ranges_idle(unsigned feature);
unsigned modwerk_controller_policy_entries(void);

#endif

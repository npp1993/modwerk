/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef MODWERK_STOCK_HOOK_RESOURCES_H
#define MODWERK_STOCK_HOOK_RESOURCES_H
#include "stock_hooks.h"
/* Source-reviewed, exact-package policies are supplied by the private manager,
 * never by a module or a host readiness flag. Words include initialization. */
struct mw_hook_buffer_claim { uint32_t words; uint8_t complete, head_safe; };
/* The claim of an effect with no reviewed exact policy entry. Stock's own effect (`stock`: a stock id that no module
 * handle owns) runs stock code with stock's slot layout: its FX2 ring is written no further than block + 0x3DA2
 * (octabam tools/remix/ledger.py; Sidechain's key window is the block's tail past it), and it shares FX2 block 2's
 * head with stock's tenants exactly as stock does. Anything else claims its whole block, with no head proof. */
#define MW_HOOK_STOCK_FX2_WORDS 0x3da3u
struct mw_hook_buffer_claim mw_hook_default_claim(unsigned kind,unsigned stock);
enum { MW_HOOK_P=0, MW_HOOK_X=1, MW_HOOK_Y=2 };
struct mw_hook_span { uint32_t address, words; uint8_t core, space; };
unsigned mw_stock_hooks_held(const struct mw_stock_hooks *);
int mw_hook_buffer_permitted(const struct mw_stock_hooks *,unsigned core,unsigned kind,unsigned block,
                             const struct mw_hook_buffer_claim *);
/* The same against an explicit held-feature mask (MW_HOOK_SIDECHAIN|MATRIX|ANALOG_BD): the stock-hook leases and the
 * controller board's held controllers together. An unknown bit refuses. */
int mw_hook_buffer_permitted_held(unsigned held,unsigned core,unsigned kind,unsigned block,
                                  const struct mw_hook_buffer_claim *);
/* Both sets must include all exact-source fixed and instance tenants, including
 * pending initialization and outgoing code through its last unbind ACK.
 * Shared X/Y/P aliases are compared across both cores. Incomplete means closed. */
int mw_hook_ranges_idle(unsigned feature,const struct mw_hook_span *live,unsigned live_count,
                        const struct mw_hook_span *target,unsigned target_count,unsigned complete_cores);
#endif

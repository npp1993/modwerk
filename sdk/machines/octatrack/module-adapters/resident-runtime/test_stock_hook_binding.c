/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "stock_hook_driver.h"
#include "stock_hook_resources.h"
#include "fxids.h"
#include <assert.h>
int modwerk_stock_hook_export_idle(void);
int modwerk_stock_hook_begin(unsigned,uint32_t,uint32_t,int);
int modwerk_stock_hook_retire(unsigned,uint32_t,uint32_t,int);
int modwerk_dsp_buffer_permitted(unsigned,unsigned,unsigned,unsigned);
const struct mw_hook_boot_core modwerk_hook_boot[2]={{0},{0}};
const fx_set modwerk_fx_modules={{1u<<26,0xffffffffu}}; /* a custom handle below 32 and every id past it */
static int saved,policy;
static unsigned controllers, head;
int modwerk_saved_set_busy(void) { return saved; }
unsigned modwerk_controller_held(void) { return controllers; }
int dl_publication_idle(void) { return 1; }
int modwerk_stock_hook_buffer_policy(unsigned core,unsigned id,struct mw_hook_buffer_claim *out) {
    (void)core;(void)id; *out=(struct mw_hook_buffer_claim){16384u,1,(uint8_t)head};return policy;
}
int main(void) {
    assert(modwerk_stock_hook_export_idle());
    saved=1;
    assert(modwerk_stock_hook_begin(1,17,23,0)==MW_HOOK_BUSY);
    assert(modwerk_stock_hook_begin(1,17,23,1)==MW_HOOK_BUSY);
    assert(modwerk_stock_hook_retire(1,17,23,1)==MW_HOOK_BUSY);
    saved=0;
    assert(modwerk_stock_hook_begin(1,17,23,1)==MW_HOOK_STATE); /* default-closed admission */
    assert(modwerk_stock_hook_begin(1,17,23,0)==MW_HOOK_OWNER);
    /* No exact policy: the whole block is claimed, so buffered FX place wherever nothing held meets it. */
    assert(modwerk_dsp_buffer_permitted(0,1,0,32) && modwerk_dsp_buffer_permitted(1,1,3,32));
    assert(modwerk_dsp_buffer_permitted(0,0,0,32) && modwerk_dsp_buffer_permitted(1,0,3,32));
    assert(!modwerk_dsp_buffer_permitted(0,1,2,32)); /* FX2 block 2 needs a reviewed head proof */
    saved=1; assert(!modwerk_dsp_buffer_permitted(0,0,0,32)); saved=0;
    policy=1;
    assert(modwerk_dsp_buffer_permitted(0,1,0,32));
    assert(!modwerk_dsp_buffer_permitted(0,1,2,32));
    head=1; assert(modwerk_dsp_buffer_permitted(0,1,2,32));
    controllers=MW_HOOK_SIDECHAIN; assert(!modwerk_dsp_buffer_permitted(0,1,2,32)); /* a held board controller's range */
    assert(modwerk_dsp_buffer_permitted(0,1,3,32));
    controllers=8u; assert(!modwerk_dsp_buffer_permitted(0,1,0,32)); /* unknown held bit */
    /* Stock's own effect (id 13) keeps T3/T7's FX2 block 2 beside a held Sidechain; a module handle (26) does not. */
    policy=0; head=0;
    controllers=MW_HOOK_SIDECHAIN|MW_HOOK_MATRIX|MW_HOOK_ANALOG_BD;
    assert(modwerk_dsp_buffer_permitted(0,1,2,13) && modwerk_dsp_buffer_permitted(1,1,2,13));
    assert(!modwerk_dsp_buffer_permitted(0,1,2,26) && !modwerk_dsp_buffer_permitted(1,1,2,26));
    assert(modwerk_dsp_buffer_permitted(0,1,3,26));
    saved=1; assert(!modwerk_dsp_buffer_permitted(0,1,2,13)); saved=0;
    controllers=0;
    assert(modwerk_stock_hook_export_idle());
    return 0;
}

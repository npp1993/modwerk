/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Explicit strong native fixture functions only. Never encode or import them
 * into a board package; they do not acquire a real IRQ or generation lock. */
#include <stdint.h>
#include <stddef.h>
struct mw_controller_write_lease {uint32_t opaque[8];};
volatile uint32_t fixture_entry=0,fixture_begin_result=0,fixture_end_result=0;
volatile uint32_t fixture_phase=0,fixture_begins=0,fixture_ends=0,fixture_storage=0;
int modwerk_controller_write_begin(uintptr_t entry,uint32_t feature,struct mw_controller_write_lease *lease)
{
    fixture_begins++;
    if(entry!=fixture_entry || feature!=4 || ((uintptr_t)lease&3u) ||
       (uintptr_t)lease<0x46c7e920u || (uintptr_t)lease>0x46c7f9fcu) return 0;
    if(fixture_begin_result!=1) return (int)fixture_begin_result;
    for(unsigned i=0;i<8;i++)lease->opaque[i]=0x719ab000u+i;
    fixture_storage=(uint32_t)(uintptr_t)lease;fixture_phase=1;return 1;
}
int modwerk_controller_write_end(struct mw_controller_write_lease *lease)
{
    fixture_ends++;
    if((uintptr_t)lease!=fixture_storage || fixture_phase!=1) return 0;
    for(unsigned i=0;i<8;i++)if(lease->opaque[i]!=0x719ab000u+i)return 0;
    fixture_phase=2;fixture_storage=0;return (int)fixture_end_result;
}

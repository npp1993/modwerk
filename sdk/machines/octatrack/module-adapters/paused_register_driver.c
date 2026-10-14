/* SPDX-License-Identifier: MIT */
/* Synthetic entry points for the actual ColdFire wrapper and task collector. */
#include "loader.h"
#include "context.h"
static unsigned collect(const struct runtime_context *context, unsigned max)
{
    unsigned count=modwerk_machine_paused((struct runtime_span *)0x47010000u,max,context);
    volatile uint32_t *out=(volatile uint32_t *)0x47010100u;
    const volatile uint32_t *in=context->registers;
    for (unsigned r=0;r<16;r++) out[r]=in[r];
    return count;
}
unsigned __attribute__((used)) one_context(void *u, const struct runtime_context *context)
{
    volatile uint32_t *args=u;
    if (u!=(void *)0x47010400u || args[0]!=0x13579bdfu) return 0;
    return collect(context,args[1]);
}
unsigned __attribute__((used)) three_context(void *u, void *span, unsigned max, const struct runtime_context *context)
{
    volatile uint32_t *args=u;
    if (u!=(void *)0x47010400u || span!=(void *)0x47010000u || args[0]!=0x13579bdfu || args[1]!=max) return 0;
    return collect(context,max);
}
RUNTIME_CONTEXT_WRAPPER(one, one_context, RUNTIME_CONTEXT_ONE, 72);
RUNTIME_CONTEXT_WRAPPER(three, three_context, RUNTIME_CONTEXT_THREE, 80);

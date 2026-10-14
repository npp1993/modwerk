/* SPDX-License-Identifier: GPL-3.0-or-later
 * Native-test-only (loader_events_fixture.cpp): the actual loader and the
 * Octatrack glue, with the generated site events when built with
 * MODWERK_RUNTIME_EVENTS. Group admission is synthetic: no board declaration
 * table. Never compile this into a base. */
#define MODWERK_RUNTIME_METADATA_EXTERNAL
#include "loader.c"
#include "sha256.c"
void *memcpy(void *to, const void *from, unsigned long length)
{ volatile uint8_t *out = to; const volatile uint8_t *in = from; for (unsigned long i = 0; i < length; i++) out[i] = in[i]; return to; }
void *memset(void *to, int value, unsigned long length)
{ volatile uint8_t *out = to; for (unsigned long i = 0; i < length; ++i) out[i] = (uint8_t)value; return to; }
int modwerk_machine_metadata_admit(const struct runtime_dsp *from, struct runtime_dsp *to,
    const struct runtime_context *context, enum runtime_metadata_operation operation)
{ (void)from; (void)to; (void)context; (void)operation; return RUNTIME_OK; }
/* The image of live module `id` (its symbols are offsets into it), 0 if none. */
uint32_t fixture_image(uint32_t id)
{
    for (unsigned i = 0; i < RUNTIME_MODULES; ++i) {
        const struct runtime_module *m = modwerk_runtime_module(i);
        if (m && m->id == id) return (uint32_t)(uintptr_t)m->dsp.image;
    }
    return 0;
}

// SPDX-License-Identifier: GPL-3.0-or-later
// QPERF for the Analog Rytm MKII: set performance locks from the QPER key.
//
// The QPER key's links are a 12-bit mask of performances. Stock adds their
// offsets together on top of the sound: every lock adds amount * value to its
// parameter, and the QPER knob sets the same amount on each linked performance.
// So, with QPER held:
//
//   turn a knob   The knob's travel since QPER went down is the total offset:
//                 it replaces the parameter's lock in every linked performance,
//                 split evenly, so together they reach it at full QPER. The
//                 kit has 48 lock slots for all performances. When a new
//                 parameter does not fit in every linked one, nothing is written.
//   PLAY          stock's clear, once per linked performance.
//   YES           each linked lock, at the QPER knob's position, goes into the
//                 kit. The locks stay.
//
// FUNC + QPER (stock's mute) and pressing pads or trigs to link are untouched.
//
// Firmware routines are reached at fixed addresses given for each OS release
// by build.json's cflags. Stock returns pointers in d0, while m68k-linux GCC
// expects them in a0, so those routines are declared as returning a word.

#include <stdint.h>

#include "analog-rytm-mk2/pages.h"

typedef unsigned long word_t;
typedef word_t (*project_singleton_t)(void);
typedef int (*track_index_of_t)(void *selection);
typedef word_t (*kit_param_set_t)(void *kit, int track);
typedef word_t (*kit_perf_t)(void *kit);
typedef word_t (*page_set_t)(void *view, int track);
typedef int (*kit_word_t)(void *kit);
typedef int (*perf_set_t)(void *perf, int index, int track, int param, int value);
typedef void (*perf_clear_t)(void *perf, int index);
typedef int (*container_index_t)(int id);
typedef int (*id_for_index_t)(int index, int machine);
typedef int (*set_read_t)(void *set, int id);
typedef void (*set_value_t)(void *set, int id, int value, int track, int a, int b);
typedef void (*fillrect_t)(void *bmp, int x0, int y0, int x1, int y1, int colour);

#define PROJECT_SINGLETON ((project_singleton_t)PROJECT_SINGLETON_AT)
#define TRACK_INDEX_OF ((track_index_of_t)TRACK_INDEX_OF_AT)
#define KIT_PARAM_SET ((kit_param_set_t)KIT_PARAM_SET_AT)
#define KIT_PERF ((kit_perf_t)KIT_PERF_AT)
#define KIT_QPER_MASK ((kit_word_t)KIT_QPER_MASK_AT)
#define KIT_QPER_MUTED ((kit_word_t)KIT_QPER_MUTED_AT)
#define PERF_SET ((perf_set_t)PERF_SET_AT)
#define PERF_CLEAR ((perf_clear_t)PERF_CLEAR_AT)
#define CONTAINER_INDEX ((container_index_t)CONTAINER_INDEX_AT)
#define ID_FOR_INDEX ((id_for_index_t)ID_FOR_INDEX_AT)
#define SET_VALUE ((set_value_t)SET_VALUE_AT)
#define FILLRECT ((fillrect_t)FILLRECT_AT)
// The performances' amounts: at full, a lock adds its whole value.
#define PERF_AMOUNT(p) (((volatile unsigned short *)PERF_AMOUNTS_AT)[p])
#define AMOUNT_FULL 0x7f80

#define PROJECT_KIT 352             // project + 352: the active kit
#define PROJECT_TRACKSEL 48         // project + 48: the track selection
#define PERF_TABLE 16               // performance object + 16: the lock table
#define VT_READ 0x28                // parameter set: read(set, id)
#define VT_PAGE_SET 0xa0            // page view: page_param_set(view, track)
#define SET_SOUND 0x18              // sound set: its live sound's source
#define VT_LIVE 0x28                // source: the live sound
#define SOUND_MACHINE 0x68          // live sound: machine byte

#define KEY_QPER 0xb1
#define KEY_YES 0x44
#define KEY_PLAY 0x51
#define KEY_FUNC 0x80
#define EV_KEY 12                   // event + 12: the key
#define EV_FLAGS 16                 // event + 16: 1 pressed, 0x10 released, 8 repeat
#define PRESSED 1
#define REPEAT 8
#define RELEASED 0x10

#define PERFS 12
#define SLOTS 48
#define SLOT_BYTES 5
#define TRACK_NONE 12               // a slot's track byte above this is empty
#define FX_TRACK 12
#define PARAM_LAST 41               // a track's 42 parameter words
#define ID_LAST 468
#define OFFSET_MAX (127 * 256)      // 8.8
#define TURNS SLOTS                 // parameters one hold can touch

typedef unsigned (*is_key_held_t)(int key);
#define IS_KEY_HELD ((is_key_held_t)IS_KEY_HELD_AT)

static int held;                    // QPER is down, without FUNC
static unsigned swallowed;          // bit 0 YES, bit 1 PLAY: their release is ours too
static struct { short id; signed char track; int total; } turns[TURNS];
static int nturns;

// A short message box. Letters are 5 x 7, left to right, top row first.
#define SHOW_TICKS 16               // ev_tick, about 20 Hz
static int show_ticks;
static const char *show_text;
static char number[8];

static const struct { char c; unsigned char rows[7]; } font[] = {
    { 'A', { 0x0e, 0x11, 0x11, 0x1f, 0x11, 0x11, 0x11 } },
    { 'C', { 0x0e, 0x11, 0x10, 0x10, 0x10, 0x11, 0x0e } },
    { 'D', { 0x1e, 0x11, 0x11, 0x11, 0x11, 0x11, 0x1e } },
    { 'E', { 0x1f, 0x10, 0x10, 0x1e, 0x10, 0x10, 0x1f } },
    { 'F', { 0x1f, 0x10, 0x10, 0x1e, 0x10, 0x10, 0x10 } },
    { 'G', { 0x0e, 0x11, 0x10, 0x17, 0x11, 0x11, 0x0e } },
    { 'H', { 0x11, 0x11, 0x11, 0x1f, 0x11, 0x11, 0x11 } },
    { 'I', { 0x1f, 0x04, 0x04, 0x04, 0x04, 0x04, 0x1f } },
    { 'K', { 0x11, 0x12, 0x14, 0x18, 0x14, 0x12, 0x11 } },
    { 'L', { 0x10, 0x10, 0x10, 0x10, 0x10, 0x10, 0x1f } },
    { 'M', { 0x11, 0x1b, 0x15, 0x15, 0x11, 0x11, 0x11 } },
    { 'N', { 0x11, 0x19, 0x15, 0x13, 0x11, 0x11, 0x11 } },
    { 'O', { 0x0e, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0e } },
    { 'P', { 0x1e, 0x11, 0x11, 0x1e, 0x10, 0x10, 0x10 } },
    { 'R', { 0x1e, 0x11, 0x11, 0x1e, 0x14, 0x12, 0x11 } },
    { 'S', { 0x0f, 0x10, 0x10, 0x0e, 0x01, 0x01, 0x1e } },
    { 'T', { 0x1f, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04 } },
    { 'U', { 0x11, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0e } },
    { '0', { 0x0e, 0x11, 0x13, 0x15, 0x19, 0x11, 0x0e } },
    { '1', { 0x04, 0x0c, 0x04, 0x04, 0x04, 0x04, 0x0e } },
    { '2', { 0x0e, 0x11, 0x01, 0x06, 0x08, 0x10, 0x1f } },
    { '3', { 0x1e, 0x01, 0x01, 0x0e, 0x01, 0x01, 0x1e } },
    { '4', { 0x02, 0x06, 0x0a, 0x12, 0x1f, 0x02, 0x02 } },
    { '5', { 0x1f, 0x10, 0x1e, 0x01, 0x01, 0x11, 0x0e } },
    { '6', { 0x06, 0x08, 0x10, 0x1e, 0x11, 0x11, 0x0e } },
    { '7', { 0x1f, 0x01, 0x02, 0x04, 0x08, 0x08, 0x08 } },
    { '8', { 0x0e, 0x11, 0x11, 0x0e, 0x11, 0x11, 0x0e } },
    { '9', { 0x0e, 0x11, 0x11, 0x0f, 0x01, 0x02, 0x0c } },
    { '+', { 0x00, 0x04, 0x04, 0x1f, 0x04, 0x04, 0x00 } },
    { '-', { 0x00, 0x00, 0x00, 0x1f, 0x00, 0x00, 0x00 } },
};
#define FONT_LEN (sizeof(font) / sizeof(font[0]))

static void show(const char *text)
{
    show_text = text;
    show_ticks = SHOW_TICKS;
}

static void show_offset(int total)
{
    int v = (total < 0 ? -total : total) >> 8, n = 0, d;
    number[n++] = total < 0 ? '-' : '+';
    for (d = 100; d >= 1; d /= 10)
        if (v >= d || d == 1)
            number[n++] = (char)('0' + v / d % 10);
    number[n] = 0;
    show(number);
}

static void *active_kit(void)
{
    return (char *)PROJECT_SINGLETON() + PROJECT_KIT;
}

static unsigned linked(void *kit)
{
    return (unsigned)KIT_QPER_MASK(kit) & 0xfff;
}

static const unsigned char *lock_table(void *perf)
{
    return *(const unsigned char **)((char *)perf + PERF_TABLE);
}

static int count_linked(unsigned mask)
{
    int i, count = 0;
    for (i = 0; i < PERFS; i++)
        if (mask >> i & 1)
            count++;
    return count;
}

// Slots a new lock for (track, param) would take.
static int slots_needed(const unsigned char *t, unsigned mask, int track, int param)
{
    int i, needed = count_linked(mask);
    unsigned have = 0;
    for (i = 0; i < SLOTS; i++, t += SLOT_BYTES)
        if (t[2] == track && t[3] == param && t[4] < PERFS && (mask >> t[4] & 1)
            && !(have >> t[4] & 1)) {
            have |= 1u << t[4];
            needed--;
        }
    return needed;
}

static int slots_free(const unsigned char *t)
{
    int i, free_slots = 0;
    for (i = 0; i < SLOTS; i++, t += SLOT_BYTES)
        if (t[2] > TRACK_NONE)
            free_slots++;
    return free_slots;
}

// The turn's running total for this parameter, 0 on its first turn this hold.
static int *turn_total(int id, int track)
{
    int i;
    for (i = 0; i < nturns; i++)
        if (turns[i].id == id && turns[i].track == track)
            return &turns[i].total;
    if (nturns == TURNS)
        return 0;
    turns[nturns].id = (short)id;
    turns[nturns].track = (signed char)track;
    turns[nturns].total = 0;
    return &turns[nturns++].total;
}

// core_params: a turn with QPER held writes locks, and stock leaves the
// parameter alone. Only a sound page's parameters have locks here: an id's
// index means a lock byte only in a sound set. Everything else passes to stock.
static int qperf_delta(void *view, int32_t id, int32_t delta, int32_t func)
{
    void *kit, *perf;
    const unsigned char *table;
    unsigned mask;
    int *total, track, param, count, part, rest, i;
    word_t project, set;
    page_set_t page_set;
    if (!held || func)
        return 0;
    page_set = *(page_set_t *)(*(word_t *)view + VT_PAGE_SET);
    set = page_set(view, -1);
    if (*(word_t *)set != SOUND_PARAM_SET_VT)
        return 0;
    param = CONTAINER_INDEX(id);
    if (param < 0 || param > PARAM_LAST)
        return 0;
    project = PROJECT_SINGLETON();
    kit = (char *)project + PROJECT_KIT;
    track = TRACK_INDEX_OF((char *)project + PROJECT_TRACKSEL);
    mask = linked(kit);
    if (!mask) {
        show("NO LINKS");
        return 1;
    }
    perf = (void *)KIT_PERF(kit);
    table = lock_table(perf);
    if (slots_needed(table, mask, track, param) > slots_free(table)) {
        show("LOCKS FULL");
        return 1;
    }
    total = turn_total(id, track);
    if (!total) {
        show("LOCKS FULL");
        return 1;
    }
    *total += delta;
    if (*total > OFFSET_MAX)
        *total = OFFSET_MAX;
    if (*total < -OFFSET_MAX)
        *total = -OFFSET_MAX;
    count = count_linked(mask);
    part = *total / count;
    rest = *total - part * count;       // the first ones carry what the split leaves
    for (i = 0; i < PERFS; i++)
        if (mask >> i & 1) {
            int value = part;
            if (rest > 0) {
                value++;
                rest--;
            } else if (rest < 0) {
                value--;
                rest++;
            }
            PERF_SET(perf, i, track, param, value);
        }
    show_offset(*total);
    return 1;
}

const struct core_param qperf_params_entry = { 1, ID_LAST, 0, qperf_delta, 0 };

// A sound parameter's id on this track: machine parameters have one per machine.
static int track_id(void *set, int param)
{
    word_t source = *(word_t *)((char *)set + SET_SOUND), sound;
    typedef word_t (*live_t)(word_t self);
    live_t live;
    if (!source)
        return 0;
    live = *(live_t *)(*(word_t *)source + VT_LIVE);
    sound = live(source);
    if (!sound)
        return 0;
    return ID_FOR_INDEX(param, *(unsigned char *)(sound + SOUND_MACHINE));
}

static void apply_linked(void *kit)
{
    void *perf = (void *)KIT_PERF(kit);
    const unsigned char *t = lock_table(perf);
    unsigned mask = linked(kit);
    int i, changed = 0;
    if (!mask) {
        show("NO LINKS");
        return;
    }
    if (KIT_QPER_MUTED(kit) & 0xff) {       // stock's result is its low byte
        show("MUTED");
        return;
    }
    for (i = 0; i < SLOTS; i++, t += SLOT_BYTES) {
        int track = t[2], param = t[3], index = t[4], id, value;
        void *set;
        set_read_t read;
        if (track >= FX_TRACK || index >= PERFS || !(mask >> index & 1) || param > PARAM_LAST)
            continue;
        value = (short)(t[0] << 8 | t[1]);
        value = value * (int)PERF_AMOUNT(index) / AMOUNT_FULL;
        if (!value)
            continue;
        set = (void *)KIT_PARAM_SET(kit, track);
        id = track_id(set, param);
        if (!id)
            continue;
        read = *(set_read_t *)(*(word_t *)set + VT_READ);
        SET_VALUE(set, id, read(set, id) + value, track, 1, 1);
        changed = 1;
    }
    show(changed ? "APPLIED" : "NOTHING");
}

static void clear_linked(void *kit)
{
    void *perf = (void *)KIT_PERF(kit);
    unsigned mask = linked(kit);
    int i;
    if (!mask) {
        show("NO LINKS");
        return;
    }
    for (i = 0; i < PERFS; i++)
        if (mask >> i & 1)
            PERF_CLEAR(perf, i);
    show("CLEARED");
}

int qperf_key(void *brain, void *event)
{
    int key = *(int *)((char *)event + EV_KEY);
    unsigned flags = *(unsigned *)((char *)event + EV_FLAGS), bit;
    (void)brain;
    if (key == KEY_QPER) {
        if (flags & RELEASED)
            held = 0;
        else if ((flags & PRESSED) && !(flags & REPEAT) && !IS_KEY_HELD(KEY_FUNC)) {
            held = 1;
            nturns = 0;
            swallowed = 0;
        }
        return 0;
    }
    if (key == KEY_YES)
        bit = 1;
    else if (key == KEY_PLAY)
        bit = 2;
    else
        return 0;
    if (flags & RELEASED) {
        if (swallowed & bit) {
            swallowed &= ~bit;
            return 1;
        }
        return 0;
    }
    if (swallowed & bit)
        return 1;                       // its repeats
    if (!held || !(flags & PRESSED) || (flags & REPEAT) || IS_KEY_HELD(KEY_FUNC))
        return 0;
    swallowed |= bit;
    if (key == KEY_YES)
        apply_linked(active_kit());
    else
        clear_linked(active_kit());
    return 1;
}

void qperf_tick(void *ctrl)
{
    if (show_ticks) {
        show_ticks--;
        ((unsigned char *)ctrl)[0x20] = 1;
    }
}

static const unsigned char *glyph_rows(char c)
{
    unsigned i;
    for (i = 0; i < FONT_LEN; i++)
        if (font[i].c == c)
            return font[i].rows;
    return 0;
}

// y counts up from the bottom row.
void qperf_draw(void *bmp, void *ctrl)
{
    const char *s;
    int n = 0, x, r, c;
    (void)ctrl;
    if (!show_ticks || !show_text)
        return;
    for (s = show_text; *s; s++)
        n++;
    x = 64 - (n * 6 - 1) / 2;
    FILLRECT(bmp, 14, 24, 113, 39, 1);
    FILLRECT(bmp, 15, 25, 112, 38, 0);
    for (s = show_text; *s; s++, x += 6) {
        const unsigned char *rows = glyph_rows(*s);
        if (!rows)
            continue;
        for (r = 0; r < 7; r++)
            for (c = 0; c < 5; c++)
                if (rows[r] >> (4 - c) & 1)
                    FILLRECT(bmp, x + c, 35 - r, x + c, 35 - r, 1);
    }
}

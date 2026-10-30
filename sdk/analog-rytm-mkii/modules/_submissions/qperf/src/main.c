// SPDX-License-Identifier: GPL-3.0-or-later
// QPERF for the Analog Rytm MKII: set performance locks from the QPER key.
//
// The QPER key's links are a 12-bit mask of performances. Stock adds their
// offsets together on top of the sound: every lock adds amount * value to its
// parameter, and the QPER knob sets the same amount on each linked performance.
// So, with QPER held:
//
//   turn a knob   Stock's own lock edit, through a locker that stands for all
//                 linked performances: it reads their sum, and a write splits
//                 evenly across them. Stock draws the locks as it does when a
//                 performance pad is held. The kit has 48 lock slots for all
//                 performances. When a new parameter does not fit in every
//                 linked one, nothing is written.
//   PLAY          stock's clear, once per linked performance. Stock keeps no
//                 copy, so we do: PLAY again, with nothing changed, undoes it.
//   YES           each linked lock, at the QPER knob's position, goes into the
//                 kit. The locks stay.
//
// FUNC + QPER (stock's mute) and pressing pads or trigs to link are untouched.
//
// Stock's amount is only written to performances linked when the knob moves, so
// the knob's position comes from one site of our own, where stock reads it.
//
// Firmware routines are reached at fixed addresses given for each OS release
// by build.json's cflags. Stock returns pointers in d0, while m68k-linux GCC
// expects them in a0, so those routines are declared as returning a word.

typedef unsigned long word_t;
typedef word_t (*project_singleton_t)(void);
typedef word_t (*kit_param_set_t)(void *kit, int track);
typedef word_t (*kit_perf_t)(void *kit);
typedef int (*kit_word_t)(void *kit);
typedef int (*perf_set_t)(void *perf, int index, int track, int param, int value);
typedef void (*perf_clear_t)(void *perf, int index);
typedef void (*perf_clear_one_t)(void *perf, int index, int track, int param);
typedef int (*id_for_index_t)(int index, int machine);
typedef int (*set_read_t)(void *set, int id);
typedef void (*set_value_t)(void *set, int id, int value, int track, int a, int b);
typedef void (*string_from_cstr_t)(void *string, const char *text, void *allocator);
typedef void (*string_dtor_t)(void *string);
typedef word_t (*mem_new_t)(unsigned size);
typedef void (*popup_ctor_t)(void *popup, void *string);
typedef void (*shared_ptr_ctor_t)(void *shared, void *object);
typedef void (*shared_ptr_release_t)(void *counts);
typedef void (*show_popup_t)(void *views, void *shared, int flag);
typedef word_t (*param_ui_t)(void);
typedef void (*set_locker_t)(void *ui, void *locker);
typedef word_t (*get_locker_t)(void *ui);
typedef void (*lock_edit_t)(void *ui, int on);
typedef void (*end_lock_edit_t)(void *ui);

#define PROJECT_SINGLETON ((project_singleton_t)PROJECT_SINGLETON_AT)
#define KIT_PARAM_SET ((kit_param_set_t)KIT_PARAM_SET_AT)
#define KIT_PERF ((kit_perf_t)KIT_PERF_AT)
#define KIT_QPER_MASK ((kit_word_t)KIT_QPER_MASK_AT)
#define PERF_SET ((perf_set_t)PERF_SET_AT)
#define PERF_CLEAR ((perf_clear_t)PERF_CLEAR_AT)
#define PERF_CLEAR_ONE ((perf_clear_one_t)PERF_CLEAR_ONE_AT)
#define ID_FOR_INDEX ((id_for_index_t)ID_FOR_INDEX_AT)
#define SET_VALUE ((set_value_t)SET_VALUE_AT)
#define STRING_FROM_CSTR ((string_from_cstr_t)STRING_FROM_CSTR_AT)
#define STRING_DTOR ((string_dtor_t)STRING_DTOR_AT)
#define MEM_NEW ((mem_new_t)MEM_NEW_AT)
#define POPUP_CTOR ((popup_ctor_t)POPUP_CTOR_AT)
#define SHARED_PTR_CTOR ((shared_ptr_ctor_t)SHARED_PTR_CTOR_AT)
#define SHARED_PTR_RELEASE ((shared_ptr_release_t)SHARED_PTR_RELEASE_AT)
#define SHOW_POPUP ((show_popup_t)SHOW_POPUP_AT)
#define PARAM_UI ((param_ui_t)PARAM_UI_AT)
#define SET_LOCKER ((set_locker_t)SET_LOCKER_AT)
#define GET_LOCKER ((get_locker_t)GET_LOCKER_AT)
#define LOCK_EDIT ((lock_edit_t)LOCK_EDIT_AT)
#define END_LOCK_EDIT ((end_lock_edit_t)END_LOCK_EDIT_AT)
// The performances' amounts: at full, a lock adds its whole value.
#define PERF_AMOUNT(p) (((volatile unsigned short *)PERF_AMOUNTS_AT)[p])
#define AMOUNT_FULL 0x7f80

#define PROJECT_KIT 352             // project + 352: the active kit
#define PERF_TABLE 16               // performance object + 16: the lock table
#define VT_READ 0x28                // parameter set: read(set, id)
#define SET_SOUND 0x18              // sound set: its live sound's source
#define VT_LIVE 0x28                // source: the live sound
#define SOUND_MACHINE 0x68          // live sound: machine byte

#define KEY_QPER 0xb1
#define KEY_YES 0x44
#define KEY_PLAY 0x51
#define KEY_FUNC 0x80
#define EV_KEY 12                   // event + 12: the key
#define EV_FLAGS 16                 // event + 16: bit 0 down (clear on release), 8 repeat
#define PRESSED 1
#define REPEAT 8
#define BRAIN_VIEWS 32              // brain + 32: the view manager
#define POPUP_BYTES 0xa0

#define PERFS 12
#define SLOTS 48
#define SLOT_BYTES 5
#define TRACK_NONE 12               // a slot's track byte above this is empty
#define FX_TRACK 12
#define PARAM_LAST 41               // a track's 42 parameter words

typedef unsigned (*is_key_held_t)(int key);
#define IS_KEY_HELD ((is_key_held_t)IS_KEY_HELD_AT)

static int held;                    // QPER is down, without FUNC
static unsigned swallowed;          // bit 0 YES, bit 1 PLAY: their release is ours too
int qperf_pot;                      // the QPER knob + 1, 0 until it first moves

// Stock's message for one pot: this replaces the 6-byte lea at its start.
__asm__(
    ".globl qperf_pot_gate\n"
    "qperf_pot_gate:\n"
    "    move.l %a2@(8),%d0\n"
    "    addq.l #1,%d0\n"
    "    move.l %d0,qperf_pot\n"
    "    lea 0x4017fa0a,%a4\n"
    "    rts\n");

// Stock's popup, opened from ev_tick so repeats open one, not dozens.
static void *views;
static const char *show_text;
static char message[24];
static unsigned char undo_table[SLOTS * SLOT_BYTES];
static unsigned undo_mask, undo_sum;    // the mask cleared, the table it left

static void show(const char *text)
{
    show_text = text;
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

// The locker stock edits through while QPER is held. Stock calls these slots.
static int locker_has_any(void *self)
{
    void *kit = active_kit();
    const unsigned char *t = lock_table((void *)KIT_PERF(kit));
    unsigned mask = linked(kit);
    int i;
    (void)self;
    for (i = 0; i < SLOTS; i++, t += SLOT_BYTES)
        if (t[2] <= TRACK_NONE && t[4] < PERFS && (mask >> t[4] & 1))
            return 1;
    return 0;
}

static void locker_clear(void *self, int track, int param)
{
    void *kit = active_kit();
    void *perf = (void *)KIT_PERF(kit);
    unsigned mask = linked(kit);
    int i;
    (void)self;
    for (i = 0; i < PERFS; i++)
        if (mask >> i & 1)
            PERF_CLEAR_ONE(perf, i, track, param);
}

static void locker_clear_all(void *self)
{
    void *kit = active_kit();
    void *perf = (void *)KIT_PERF(kit);
    unsigned mask = linked(kit);
    int i;
    (void)self;
    for (i = 0; i < PERFS; i++)
        if (mask >> i & 1)
            PERF_CLEAR(perf, i);
}

// Sums what stock shows back, so a turn carries on from the total on the knob.
static void locker_set(void *self, int track, int param, int value)
{
    void *kit = active_kit();
    void *perf = (void *)KIT_PERF(kit);
    const unsigned char *table = lock_table(perf);
    unsigned mask = linked(kit);
    int count, part, rest, i;
    (void)self;
    if (!mask) {
        show("NOTHING LINKED");
        return;
    }
    if (slots_needed(table, mask, track, param) > slots_free(table)) {
        show("LOCK MEM FULL!");
        return;
    }
    count = count_linked(mask);
    part = value / count;
    rest = value - part * count;        // the first ones carry what the split leaves
    for (i = 0; i < PERFS; i++)
        if (mask >> i & 1) {
            int one = part;
            if (rest > 0) {
                one++;
                rest--;
            } else if (rest < 0) {
                one--;
                rest++;
            }
            PERF_SET(perf, i, track, param, one);
        }
}

static int locker_get(void *self, int track, int param)
{
    void *kit = active_kit();
    const unsigned char *t = lock_table((void *)KIT_PERF(kit));
    unsigned mask = linked(kit);
    int i, total = 0;
    (void)self;
    for (i = 0; i < SLOTS; i++, t += SLOT_BYTES)
        if (t[2] == track && t[3] == param && t[4] < PERFS && (mask >> t[4] & 1))
            total += (short)(t[0] << 8 | t[1]);
    return total;
}

static int locker_has(void *self, int track, int param)
{
    void *kit = active_kit();
    const unsigned char *t = lock_table((void *)KIT_PERF(kit));
    unsigned mask = linked(kit);
    int i;
    (void)self;
    for (i = 0; i < SLOTS; i++, t += SLOT_BYTES)
        if (t[2] == track && t[3] == param && t[4] < PERFS && (mask >> t[4] & 1))
            return 1;
    return 0;
}

static void locker_never(void *self)
{
    (void)self;                         // the object is static: never destroyed
}

// PerformanceParamLocker's slots, its last two kept: relative, and lockable(id).
static const void *const locker_vtable[] = {
    locker_never, locker_never, locker_has_any, locker_clear, locker_clear_all,
    locker_set, locker_get, locker_has,
    (const void *)LOCKER_RELATIVE_AT, (const void *)LOCKER_LOCKABLE_AT,
};
static struct { const void *const *vtable; } locker = { locker_vtable };

static void locker_install(void)
{
    void *ui = (void *)PARAM_UI();
    if (GET_LOCKER(ui))
        return;                         // a pad or trig holds it: stock's
    SET_LOCKER(ui, &locker);
    LOCK_EDIT(ui, 1);
}

static void locker_remove(void)
{
    void *ui = (void *)PARAM_UI();
    if (GET_LOCKER(ui) == (word_t)&locker)
        END_LOCK_EDIT(ui);
}

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

// PERFORMANCE 3 APPLIED, or PERFORMANCES APPLIED with several linked.
static void show_performances(unsigned mask, const char *done)
{
    const char *name = count_linked(mask) == 1 ? "PERFORMANCE " : "PERFORMANCES ";
    char *out = message;
    int number = 1;
    while (*name)
        *out++ = *name++;
    if (count_linked(mask) == 1) {
        while (!(mask >> (number - 1) & 1))
            number++;
        if (number > 9)
            *out++ = '1';
        *out++ = (char)('0' + number % 10);
        *out++ = ' ';
    }
    while (*done)
        *out++ = *done++;
    *out = 0;
    show(message);
}

static void apply_linked(void *kit)
{
    void *perf = (void *)KIT_PERF(kit);
    const unsigned char *t = lock_table(perf);
    unsigned mask = linked(kit);
    int i, seen = 0;
    for (i = 0; i < SLOTS; i++, t += SLOT_BYTES) {
        int track = t[2], param = t[3], index = t[4], id, value, amount;
        void *set;
        set_read_t read;
        if (track >= FX_TRACK || index >= PERFS || !(mask >> index & 1) || param > PARAM_LAST)
            continue;
        seen = 1;
        amount = qperf_pot ? (qperf_pot - 1) << 7 : (int)PERF_AMOUNT(index);
        value = (short)(t[0] << 8 | t[1]);
        value = value * amount / AMOUNT_FULL;
        if (!value)
            continue;
        set = (void *)KIT_PARAM_SET(kit, track);
        id = track_id(set, param);
        if (!id)
            continue;
        read = *(set_read_t *)(*(word_t *)set + VT_READ);
        SET_VALUE(set, id, read(set, id) + value, track, 1, 1);
    }
    if (seen)
        show_performances(mask, "APPLIED");
    else
        show("NOTHING TO APPLY");
}

static unsigned table_sum(const unsigned char *t)
{
    unsigned sum = 0;
    int i;
    for (i = 0; i < SLOTS * SLOT_BYTES; i++)
        sum = (sum << 1 | sum >> 31) + t[i];
    return sum;
}

static void clear_linked(void *kit)
{
    void *perf = (void *)KIT_PERF(kit);
    const unsigned char *t = lock_table(perf);
    unsigned mask = linked(kit);
    int i;
    if (locker_has_any(0)) {
        for (i = 0; i < SLOTS * SLOT_BYTES; i++)
            undo_table[i] = t[i];
        locker_clear_all(0);
        undo_mask = mask;
        undo_sum = table_sum(t);
        show_performances(mask, "CLEARED");
    } else if (mask && mask == undo_mask && table_sum(t) == undo_sum) {
        const unsigned char *u = undo_table;
        for (i = 0; i < SLOTS; i++, u += SLOT_BYTES)
            if (u[2] <= TRACK_NONE && u[4] < PERFS && (mask >> u[4] & 1))
                PERF_SET(perf, u[4], u[2], u[3], (short)(u[0] << 8 | u[1]));
        undo_mask = 0;
        show("UNDO CLEAR");
    } else {
        show("NOTHING TO CLEAR");
    }
}

int qperf_key(void *brain, void *event)
{
    int key = *(int *)((char *)event + EV_KEY);
    unsigned flags = *(unsigned *)((char *)event + EV_FLAGS), bit;
    views = *(void **)((char *)brain + BRAIN_VIEWS);
    if (key == KEY_QPER) {
        if (!(flags & PRESSED)) {
            if (held)
                locker_remove();
            held = 0;
        } else if (!(flags & REPEAT) && !IS_KEY_HELD(KEY_FUNC)) {
            held = 1;
            swallowed = 0;
            locker_install();
        }
        return 0;
    }
    if (key == KEY_YES)
        bit = 1;
    else if (key == KEY_PLAY)
        bit = 2;
    else
        return 0;
    if (!(flags & PRESSED)) {
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

// As stock's clear shows its own.
void qperf_tick(void *ctrl)
{
    char string[4], allocator;
    struct { void *object; void *counts; } shared;
    void *popup;
    (void)ctrl;
    if (!show_text || !views)
        return;
    STRING_FROM_CSTR(string, show_text, &allocator);
    show_text = 0;
    popup = (void *)MEM_NEW(POPUP_BYTES);
    POPUP_CTOR(popup, string);
    SHARED_PTR_CTOR(&shared, popup);
    SHOW_POPUP(views, &shared, 0);
    SHARED_PTR_RELEASE(&shared.counts);
    STRING_DTOR(string);
}

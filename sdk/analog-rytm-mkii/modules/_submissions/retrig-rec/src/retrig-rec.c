// Retrig Rec for the Analog Rytm MKII (OS 1.74): a Modwerk elemod module.
//
// In LIVE RECORDING stock records a retrig hold as one trig, then tries to add a
// trigless lock on each later step, and its held-note wipe removes most of those.
// This module records what was played instead: every hit of a pad's retrig series
// becomes a real trig with the velocity it sounded at, at the time it sounded.
//
// Stock's series runs in the audio block: a tick counter, 960 ticks a whole note,
// fires on the ticks where the count is a multiple of the rate's period and reloads
// from 1 to 960. ev_render_out follows the count and, for each hit, closes the hit
// before it and starts this one by queueing the note events a pad would queue to the
// sequencer task. Stock's own recorder then writes the trig. The module's order is
// before Retrig Grid's, which rewrites the count in the same block.
//
// A step holds one trig. A rate faster than the track's step records a trig on the
// first hit of each whole block of steps, with the step retrig that plays the rest:
// two hits a step at 1/32, three hits in two steps at 1/24.
//
// The stock sites, in retrig-rec.s: the RETRIG menu's step writes off, recorded retrig
// hits keep their timing with quantize on, and a recorded retrig takes the menu's
// VEL.CUR.

#include <stdint.h>

#define TRACKS 12
#define WHOLE 960               // ticks in a whole note: the counter's span
#define KEEP_TIMING 256         // added to a queued hit's micro timing: see retrig-rec.s
#define EV_NOTE 0x0d

// OS 1.74 locations (build.json release cflags)
#define RT_ACTIVE ((volatile uint8_t *)RT_ACTIVE_AT)        // [t] 1: a pad's series
#define RT_COUNT ((volatile int32_t *)RT_COUNT_AT)          // [t] 960..1
#define RT_RATE(t) (*(volatile int32_t *)(RT_TEMPLATE_AT + 56 * (t) + 36))  // RETRIG 0..16
#define RT_CURVE(t) (*(volatile int32_t *)(RT_TEMPLATE_AT + 56 * (t) + 44)) // VEL.CUR
#define RT_VELOCITY ((volatile uint16_t *)RT_VELOCITY_AT)   // [t] the hit's, 8.8
#define RT_FIRES ((const uint16_t *)RT_FIRES_AT)            // [count] the rates firing there
#define CLOCK (*(volatile uint32_t *)CLOCK_AT)
#define NOTE_RING ((volatile uint8_t *)NOTE_RING_AT)        // 16 events of 32 bytes
#define NOTE_RING_NEXT (*(volatile uint32_t *)NOTE_RING_NEXT_AT)
#define NOTE_QUEUE (*(volatile uint32_t *)NOTE_QUEUE_AT)
#define NOTE_START ((volatile uint32_t *)NOTE_START_AT)     // [t * 128 + note] clock / 2
#define SEQ_PATTERN (*(volatile int8_t *)SEQ_PATTERN_AT)
#define SPEED_PULSES ((const int32_t *)SPEED_PULSES_AT)     // 3, 4, 6, 8, 12, 24, 48

// The pattern in memory (85760 bytes), and a track in it (917 bytes)
#define PATTERN(p) ((const volatile int8_t *)PATTERNS_AT + 85760 * (p))
#define PAT_SCALE 85689         // 1: ADVANCED, each track its own length and speed
#define PAT_SPEED 85690         // 0..6, as SPEED_PULSES
#define TRK_SPEED 711
#define PULSE_TICKS 10

// Stock routines (build.json defsym). They return pointers in d0, so these return integers.
extern uint32_t STOCK_APP(void);
extern uint32_t STOCK_LIVE_REC(uint32_t app);
extern void STOCK_QUEUE_POST(uint32_t queue, void *event);
extern void STOCK_STEP_PLACE(uint32_t clock, int32_t track, uint8_t *place);
extern void STOCK_STEP_SET_RATE(uint32_t track, int32_t step, int32_t rate);
extern void STOCK_STEP_SET_CURVE(uint32_t track, int32_t step, int32_t curve);

// RETRIG 1/1 .. 1/80, in ticks
static const int16_t period[17] = { 960, 480, 320, 240, 192, 160, 120, 96, 80, 60, 48, 40, 30, 24, 20, 15, 12 };

static int32_t seen[TRACKS];
static uint8_t press[TRACKS][32];   // the press's note event
static uint8_t have[TRACKS];
static uint16_t hits[TRACKS];
static uint32_t started[TRACKS];    // this hit's time, clock / 2

// The events this module queues: stock's own ring has no lock for the audio block.
static uint8_t events[32][32];
static uint8_t next_event;

static void queue(const uint8_t *event)
{
    uint8_t *e = events[next_event++ & 31];
    int i;

    for (i = 0; i < 32; i++)
        e[i] = event[i];
    STOCK_QUEUE_POST(NOTE_QUEUE, e);
}

// A press queues its note event before the audio block arms the series.
static void find_press(int t)
{
    unsigned slot = (NOTE_RING_NEXT - 1) & 15, n, i;

    for (n = 0; n < 8; n++, slot = (slot - 1) & 15) {
        volatile uint8_t *e = NOTE_RING + 32 * slot;

        if (e[0] == EV_NOTE && e[7] == 0 && e[8] == t) {
            for (i = 0; i < 32; i++)
                press[t][i] = e[i];
            started[t] = NOTE_START[(t << 7) + press[t][16]];
            hits[t] = 0;
            have[t] = 1;
            return;
        }
    }
}

// Ticks in a step of track t, at its speed.
static int step_ticks(int t)
{
    const volatile int8_t *pattern;
    int p = SEQ_PATTERN, speed;

    if (p < 0 || p >= 128)
        return 6 * PULSE_TICKS;
    pattern = PATTERN(p);
    speed = pattern[PAT_SCALE] == 1 ? pattern[917 * t + TRK_SPEED] : pattern[PAT_SPEED];
    if (speed < 0 || speed > 6)
        return 6 * PULSE_TICKS;
    return SPEED_PULSES[speed] * PULSE_TICKS;
}

// Hits in the shortest run of whole steps that holds whole hits.
static int hits_in_block(int ticks, int step)
{
    int a = ticks, b = step;

    if (ticks >= step)
        return 1;
    while (b) {
        int c = a % b;

        a = b;
        b = c;
    }
    return step / a;
}

// Hit: close the one before it, as a release would, and start this one.
static void hit(int t)
{
    uint8_t on[32], off[32], place[4];   // the place is three bytes
    uint32_t now = CLOCK >> 1, held;
    int rate = RT_RATE(t), step, block, velocity, micro, i;

    if (!have[t])
        find_press(t);
    if (!have[t] || rate < 0 || rate > 16)
        return;
    step = step_ticks(t);
    block = hits_in_block(period[rate], step);
    if (++hits[t] % block)
        return;
    STOCK_STEP_PLACE(CLOCK, t, place);
    velocity = RT_VELOCITY[t] >> 8;
    if (velocity < 1)
        velocity = 1;
    if (velocity > 127)
        velocity = 127;
    micro = (int8_t)place[1];
    held = now - started[t];

    for (i = 0; i < 32; i++)
        off[i] = 0;
    off[0] = EV_NOTE;
    off[7] = 1;
    off[8] = t;
    off[15] = press[t][15];
    off[16] = press[t][16];
    off[20] = held >> 24;
    off[21] = held >> 16;
    off[22] = held >> 8;
    off[23] = held;
    off[24] = 1;
    off[25] = 1;
    off[29] = place[0];
    off[30] = micro < 0 ? 0xff : 0;
    off[31] = place[1];
    queue(off);

    for (i = 0; i < 32; i++)
        on[i] = press[t][i];
    on[17] = velocity;
    on[20] = period[rate] < step ? rate : 0xff;
    on[28] = 0;
    on[29] = place[0];
    micro += KEEP_TIMING;
    on[30] = micro >> 8;
    on[31] = micro;
    queue(on);

    started[t] = now;                   // the release closes the last hit
    NOTE_START[(t << 7) + press[t][16]] = now;
}

// ev_render_out: stock's series state for this block in place. Nothing but three
// reads a block until a pad retriggers.
void retrig_rec_render(void)
{
    const volatile uint32_t *active = (const volatile uint32_t *)RT_ACTIVE;
    int t;

    if (!(active[0] | active[1] | active[2])) {
        for (t = 0; t < TRACKS; t++) {
            seen[t] = -1;
            have[t] = 0;
        }
        return;
    }
    for (t = 0; t < TRACKS; t++) {
        int32_t c;

        if (!RT_ACTIVE[t]) {
            seen[t] = -1;
            have[t] = 0;
            continue;
        }
        c = RT_COUNT[t];
        if (seen[t] >= 0 && c != seen[t]) {
            int fired = c == WHOLE && seen[t] == 1;
            int rate = RT_RATE(t);

            // a count that did not step down was set by another module
            if (c == seen[t] - 1 && rate >= 0 && rate <= 16)
                fired = ((RT_FIRES[c] * 2) >> rate) & 1;
            if (fired && STOCK_LIVE_REC(STOCK_APP()))
                hit(t);
        }
        seen[t] = c;
    }
}

// The recorder's call that sets a step's retrig rate (retrig-rec.s): also the menu's VEL.CUR.
void retrig_rec_step_rate(uint32_t track, int step, int rate, int t)
{
    STOCK_STEP_SET_RATE(track, step, rate);
    STOCK_STEP_SET_CURVE(track, step, RT_CURVE(t));
}

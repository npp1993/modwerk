#!/usr/bin/env python3
"""Preview the docking startup's screen without firmware: a host build of boot_anim.c on a simulated clock.

Compiles boot_anim.c for the host (MODWERK_HOST, as test_boot_anim.c does) with public_art.py's art, plays the score
at 20 ms per frame and writes the LCD frames as a GIF, holding the last frame for HOLD ms so it can be seen. The
panel lamps are not drawn: their positions come from the stock lamp table at run time. This shows the authored
source, not the firmware: the emulator check (scripts/verify-startup-beta.py) captures the real image.

  python3 -B sdk/runtime/startup/preview.py OUT.gif
"""
import argparse
from pathlib import Path
import struct
import subprocess
import tempfile
from PIL import Image
import public_art

HERE = Path(__file__).resolve().parent
STEP, SCALE, HOLD = 20, 6, 1500
HARNESS = r'''
#include <stdio.h>
#include <string.h>
#include "boot_anim.c"
volatile uint32_t host_dtcn3;
uint32_t host_mkii = 1, host_intensity = 1;
int32_t host_lamps[134];
const uint32_t host_white[3] = {0x0c, 0x30, 0x44};
static unsigned char frame[1024];
static FILE *out;
void host_clear(void *w, int a, int b) { (void)w; (void)a; (void)b; }
void host_led_on(int id) { (void)id; }
void host_led_off(int id) { (void)id; }
void host_led_level(int id, int level) { (void)id; (void)level; }
void host_led_send(void) {}
void host_palette(int id, int reg, int r, int g, int b) { (void)id; (void)reg; (void)r; (void)g; (void)b; }
void host_scheme(int l, int bl, int li, int k) { (void)l; (void)bl; (void)li; (void)k; }
void host_compose(void)
{
    memset(frame, 0, sizeof frame);
    modwerk_boot_draw(frame);
    fwrite(&now, sizeof now, 1, out);
    fwrite(frame, 1, sizeof frame, out);
    host_dtcn3 += 132000u * STEP;
}
int main(int argc, char **argv)
{
    int window;
    out = fopen(argv[argc - 1], "wb");
    modwerk_boot_run(&window);
    return fclose(out);
}
'''


def frames():
    with tempfile.TemporaryDirectory(prefix='modwerk-startup-preview-') as temp:
        work = Path(temp)
        (work / 'boot_art.h').write_text(public_art.header())
        (work / 'preview.c').write_text(HARNESS)
        subprocess.run(['cc', '-std=c99', '-O2', '-Wall', '-Wextra', '-Werror', '-DMODWERK_HOST', '-DSTEP=%d' % STEP,
                        '-I', str(work), '-I', str(HERE), str(work / 'preview.c'), '-o', str(work / 'preview')], check=True)
        subprocess.run([str(work / 'preview'), str(work / 'frames.bin')], check=True)
        data = (work / 'frames.bin').read_bytes()
    for at in range(0, len(data), 1028):
        lcd = data[at + 4:at + 1028]
        yield {(x, y) for x in range(128) for y in range(64) if lcd[x * 8 + ((63 - y) >> 3)] & (0x80 >> ((63 - y) & 7))}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('output', type=Path)
    output = parser.parse_args().output
    shown = list(frames())
    if shown[-1] != public_art.final_pixels():
        raise SystemExit('The last frame is not the authored final frame.')
    images, durations = [], []
    for i, pixels in enumerate(shown):
        if i and pixels == shown[i - 1]:
            durations[-1] += STEP
            continue
        image = Image.new('1', (128, 64))
        for p in pixels:
            image.putpixel(p, 1)
        images.append(image.resize((128 * SCALE, 64 * SCALE), Image.NEAREST))
        durations.append(STEP)
    durations[-1] += HOLD
    images[0].save(output, save_all=True, append_images=images[1:], duration=durations, loop=0)


if __name__ == '__main__':
    main()

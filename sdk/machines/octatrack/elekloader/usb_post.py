# SPDX-License-Identifier: GPL-3.0-or-later
"""The POST producer's stock-data recipe; words come only from local 1.40C.

The source has no gain table. Its 256 DSP words are expanded to ColdFire
32-bit longs privately, then stripped from the distributable base package.
"""
import math

LAYOUT = 'USB AUDIO OUT TRACKS POST'
CURVE = 'usb-post-xlv'
ADDRESS = 0x6c00
COUNT = 256


def validate(words):
    words = list(words)
    if len(words) != COUNT or any(type(w) is not int or not 0 <= w <= 0xffffff for w in words):
        raise ValueError('USB POST needs exactly 256 stock quarter-sine words.')
    for i, word in enumerate(words):
        expected = round(math.sin(2 * math.pi * i / 1024) * 0x7fffff)
        if abs(word - expected) > 64 or i and word <= words[i - 1]:
            raise ValueError('USB POST gain curve differs from the stock quarter-sine table.')
    return words


def read(read_word):
    return validate(read_word(1, ADDRESS + i) for i in range(COUNT))


def image_words(image, device, dsp):
    records = dsp.records(image, device, 'A')
    def word(space, address):
        for sp, lo, count, first in records:
            if sp == space and lo <= address < lo + count:
                return dsp.w24(image, first - device.main_load + 3 * (address - lo))
        raise ValueError('Stock core 0 does not contain the USB POST gain table.')
    return read(word)


def include(words):
    return '.macro POST_XLV_TABLE\n' + ''.join('    .long 0x%06x\n' % w for w in validate(words)) + '.endm\n'


def width(fill):
    """Only this named, bounded recipe may expand DSP words to 32-bit data."""
    if 'curve' not in fill:
        return 3
    if (set(fill) != {'curve', 'tag', 'first', 'count', 'section', 'offset'} or
            fill['curve'] != CURVE or fill['tag'] != 'A' or
            type(fill['first']) is not int or fill['first'] != 0 or
            type(fill['count']) is not int or fill['count'] != COUNT or
            not isinstance(fill['section'], str) or not fill['section'] or
            type(fill['offset']) is not int or fill['offset'] < 0 or fill['offset'] % 2):
        raise ValueError('Unsupported USB POST stock-data fill.')
    return 4


def fill(section, offset):
    result = dict(curve=CURVE, tag='A', first=0, count=COUNT, section=section, offset=offset)
    width(result)
    return result

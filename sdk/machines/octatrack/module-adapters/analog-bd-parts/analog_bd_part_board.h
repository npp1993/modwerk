/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef MODWERK_ANALOG_BD_PART_BOARD_H
#define MODWERK_ANALOG_BD_PART_BOARD_H
#include "analog_bd_part_restore.h"
/* 1 when [at, at+n) is a permitted board access for the AB conversion: any of
 * the 138 Part records (read or write), or, read only, the bank pointer, the
 * two clipboard kind words or the 12 stock FLEX defaults. */
int mw_ab_part_board_access(uint32_t at, unsigned n, int write);
/* Both require the stable machine lock (SR level 4 or above); otherwise UNKNOWN.
 * check: read-only plan for metadata PREPARE (CLEAR or PLANNED admits, UNKNOWN refuses).
 * retire: the conversion at metadata SWITCH; only CLEAR may retire an AB image. */
int mw_ab_board_check(void);
int mw_ab_board_retire(void);
#endif

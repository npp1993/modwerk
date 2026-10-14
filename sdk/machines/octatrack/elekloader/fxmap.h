/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef MODWERK_FXMAP_H
#define MODWERK_FXMAP_H
#include <stdint.h>
/* Nonmutating inspections: unlike legacy getters, a corrupt map never seeds
 * or adopts a new identity. All checked operations retain the stable lock. */
uint32_t modwerk_fxmap_checked_generation(void);
int modwerk_fxmap_current(unsigned,uint32_t,unsigned,const char *);
int modwerk_fxmap_allows_checked(unsigned,uint32_t);
int modwerk_fxmap_assign_checked(unsigned,uint32_t,unsigned,const char *);
#endif

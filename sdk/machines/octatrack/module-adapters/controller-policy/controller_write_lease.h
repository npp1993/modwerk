/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef MODWERK_CONTROLLER_WRITE_LEASE_H
#define MODWERK_CONTROLLER_WRITE_LEASE_H
#include "controller_association.h"
#include "loader.h"
#define MW_CONTROLLER_WRITE_POLICY_CAPACITY 24u
struct mw_controller_write_lease { uint32_t opaque[8]; };
/* Trusted board source table. Version and both continuation offsets belong
 * to the exact encoded/source digest; uploaded bytes never supply a row.
 * count=0 is the production preparation boundary, not a wildcard policy. */
struct mw_controller_write_policy {
    struct mw_controller_identity identity;
    uint32_t version, image_bytes, entry, begin_return, end_return;
};
extern const struct mw_controller_write_policy modwerk_controller_write_policies[];
extern const unsigned modwerk_controller_write_policy_count;
extern struct mw_controller_registry modwerk_controller_registry;
/* Mandatory actual board facts under the retained level-4 lock. The owner
 * read pointer stays lossless and is the alias module code runs from: entry
 * and return PCs are checked there. cached_image is independently derived
 * from that exact allocation's pool geometry, never a caller's alias flag. */
int modwerk_controller_write_resolve(uintptr_t,struct runtime_owner *,uintptr_t *cached_image);
/* Machine glue: the running task's measured stack bounds; 0 when unknown. */
int modwerk_machine_stack(uintptr_t *lo,uintptr_t *hi);
int modwerk_controller_write_stack(uintptr_t caller_sp,uintptr_t lease,unsigned frame_bytes);
int modwerk_controller_write_begin(uintptr_t,uint32_t,struct mw_controller_write_lease *);
int modwerk_controller_write_end(struct mw_controller_write_lease *);
#endif

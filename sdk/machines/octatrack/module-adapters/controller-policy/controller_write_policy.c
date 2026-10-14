/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "controller_write_lease.h"
/* Board-compiled reviewed rows, one per exact encoded/source controller
 * binding and leased entry: {identity, version, image_bytes, entry,
 * begin_return, end_return}. None is in this source: a private base build
 * fills them from stock_hook_controllers.py's rows for that same base link
 * (build_core.py --controller-policies). The storage is always the full
 * capacity plus the version-0 sentinel, so filling rows never moves a symbol
 * the encoded packages name; the count is the rows given. */
#ifndef MW_REVIEWED_CONTROLLER_POLICIES
#define MW_REVIEWED_CONTROLLER_POLICIES /* none */
#endif
#define MW_POLICY_ROWS (sizeof (const struct mw_controller_write_policy[]){ MW_REVIEWED_CONTROLLER_POLICIES {.version = 0} } / \
                        sizeof(struct mw_controller_write_policy) - 1u)
const struct mw_controller_write_policy modwerk_controller_write_policies[MW_CONTROLLER_WRITE_POLICY_CAPACITY + 1u] = {
    MW_REVIEWED_CONTROLLER_POLICIES {.version = 0}
};
const unsigned modwerk_controller_write_policy_count = MW_POLICY_ROWS;
typedef char modwerk_controller_write_policies_bounded[MW_POLICY_ROWS <= MW_CONTROLLER_WRITE_POLICY_CAPACITY ? 1 : -1];
typedef char modwerk_controller_write_policy_row_is_96_bytes[
    sizeof(struct mw_controller_write_policy) == 96u ? 1 : -1];

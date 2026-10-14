/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef MODWERK_CONTROLLER_TRANSPORT_H
#define MODWERK_CONTROLLER_TRANSPORT_H
#include "controller_association.h"
#include "transfer.h"

/* Board-owned providers only. Each callback runs with the actual stable
 * machine lock retained. Exact compiled declaration/source binding, owned
 * reconstruction and persistent resource roots are mandatory; an uploaded
 * policy or a caller readiness flag is never a provider. Missing facts close
 * initialization. The production empty policy supplies none of these. */
struct mw_controller_transport_policy {
    int (*owns_image)(void *,const struct mw_controller_binding *);
    int (*resources_idle)(void *,const struct mw_controller_binding *);
    int (*writes_blocked)(void *);
    int (*publication_confirmed)(void *,const struct mw_controller_binding *);
    int (*roots_clear)(void *,const struct mw_controller_binding *);
    /* Exactly this declaration's immutable authored reset stream at the
     * registry-derived offset. Words outlive checked transport release. */
    int (*reset_source)(void *,const struct mw_controller_binding *,unsigned core,
        uint32_t offset,const uint32_t **words,unsigned *count);
    /* Known receiver ownership from actual boot/owned jobs or independent
     * checked observation; no guessed expected mask or host authority. */
    int (*receiver_mask)(void *,const struct mw_controller_binding *,unsigned core,uint32_t *);
};
struct mw_controller_transport {
    struct mw_controller_registry *registry;
    const struct mw_controller_transport_policy *policy;
    void *context;
    struct dl_owned_job receipts[2];
    struct mw_controller_job jobs[2];
    uint8_t slot[2], held[2], observed[2], released[2], closed[2];
};
/* Boot-only on zero-owned context/empty registry. No declarations or image
 * generations are minted here; bind through the existing checked registry. */
int mw_controller_transport_init(struct mw_controller_transport *,struct mw_controller_registry *,
    const struct mw_controller_transport_policy *,void *);
/* Only binding/core/operation are requested. Offset/count/reset data and
 * expected/desired masks come from registry + exact compiled board source. */
int mw_controller_transport_begin(struct mw_controller_transport *,const struct mw_controller_binding *,unsigned core,unsigned operation);
/* Actual sole-job progress feeds registry observations, then checked storage
 * release precedes registry release. Unknown work quarantines both versions;
 * late completion drains storage without promotion. No hardware ACK or
 * publication qualification is claimed by this source bridge. */
int mw_controller_transport_poll(struct mw_controller_transport *,const struct mw_controller_binding *,unsigned core);
#endif

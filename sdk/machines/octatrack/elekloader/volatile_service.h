/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef MODWERK_VOLATILE_SERVICE_H
#define MODWERK_VOLATILE_SERVICE_H
#include "journal.h"
#define MVS_FRAME_BYTES 4096u
#define MVS_STATUS_BYTES 212u
#define MVS_HEADER_BYTES 96u
#define MVS_QUIET_TICKS 600u
#define MVS_ABSOLUTE_TICKS 7200u
enum mvs_phase { MVS_IDLE,MVS_RECEIVING,MVS_VERIFIED,MVS_INITIALIZING,MVS_PUBLISHING,
    MVS_STOPPED_TRIAL,MVS_RUNNING_TRIAL,MVS_ROLLBACK,MVS_QUARANTINE };
enum mvs_result { MVS_OK,MVS_QUEUED,MVS_BUSY,MVS_STATE,MVS_IDENTITY,MVS_STALE,MVS_LIMIT,
    MVS_LENGTH,MVS_CONFLICT,MVS_HASH,MVS_REFUSED,MVS_PENDING,MVS_QUARANTINED,MVS_UNSUPPORTED };
struct mvs_record { uint32_t module,offset,length,mask; uint8_t digest[32]; };
/* One engine owner; ISR only queues bounded immutable frames and copies the
 * cached status. Stage is the exclusive existing boot/upload reservation. */
struct mvs_service {
    uint8_t *stage,*frame;
    uint32_t capacity,sequence,transaction,generation,received,total;
    volatile uint32_t began,heard;
    uint32_t touched,frame_bytes;
    uint8_t base[32],session[32],baseline[32],offer[32],current[32];
    uint8_t status[MVS_STATUS_BYTES];
    struct mvs_record records[RUNTIME_JOURNAL_ROWS];
    uint32_t participants[RUNTIME_JOURNAL_ROWS];
    uint16_t count,participant_count,prepare_at;
    volatile uint8_t phase,queued,expired;
    uint8_t result,baseline_known,current_known,trial_running,verifying;
};
int modwerk_volatile_init(struct mvs_service *,uint8_t *,uint32_t,const uint8_t[32],const uint8_t[32]);
int modwerk_volatile_queue(struct mvs_service *,const uint8_t *,uint32_t);
unsigned modwerk_volatile_status(const struct mvs_service *,uint8_t *);
int modwerk_volatile_tick(struct mvs_service *,uint32_t);
void modwerk_volatile_reset(struct mvs_service *);
void modwerk_volatile_service(struct mvs_service *,uint32_t);
int modwerk_volatile_busy(const struct mvs_service *);
/* modset.c, the board's saved set. Keep checks the kept set against it under
 * the stable lock, then seals it once the journal accepted; the engine saves
 * it. MWVS flag bits 4 and 5 (unsaved): not yet confirmed on the card, and
 * its last card write failed. */
int modwerk_modset_keep(const uint8_t *const[],const uint32_t[],unsigned,const uint8_t[MU_DIGEST_BYTES]);
void modwerk_modset_kept(void);
unsigned modwerk_modset_unsaved(void);
#endif

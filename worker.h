#ifndef HANDOFF_WORKER_H
#define HANDOFF_WORKER_H

#include <pthread.h>
#include <stdint.h>
#include <linux/netfilter.h>

#define WORKER_MAX_REORDER_COUNT (1000)

typedef struct {
    const char *id;
    pthread_mutex_t rwnd_lock, reorder_lock, dedup_lock, drop_lock;
    /* Mark for the packets */
    uint32_t mark;
    /* Whether to reorder and the offset */
    int do_reorder;
    int reorder_count, reorder_offset, reorder_id_cur;
    uint32_t *reorder_ids;
    /* Whether to drop packets and the number */
    int do_drop;
    int drop_count;

    // solution
    /* Whether to modify the rwnd field and the value */
    int do_rwnd; // whether to use tune_rwnd
    uint16_t tune_rwnd;

    int do_burst;
    int burst_sample_interval;
    uint64_t data_rcvd;

    int do_adapt;

    /* Whether to suppress dup ACKs and the last ack number */
    int do_dedup;
    uint32_t last_ack; // store as host int
} worker_ctx;

/* worker_callback is the callback function for the NFQUEUE. The data must be a pointer to a worker_ctx struct. */
int worker_callback(struct nfq_q_handle *qh, struct nfgenmsg *nfmsg, struct nfq_data *nfa, void *data);

/* worker_init_ctx initializes worker_ctx before use */
void worker_init_ctx(worker_ctx *ctx, const char *id);

/* worker_set_mark sets the worker's mark function */
void worker_set_mark(worker_ctx *ctx, uint32_t mark);

void worker_sol_update(worker_ctx *ctx, int rwnd);

/* worker_set_rwnd sets the worker's rwnd function */
void worker_set_rwnd(worker_ctx *ctx, uint16_t rwnd);

void worker_set_burst(worker_ctx *ctx, int enable, int rwnd);

void worker_set_adapt(worker_ctx *ctx, int enable, int rwnd);

void worker_init_tcp_sched(worker_ctx *ctx, int do_rwnd);

/* worker_set_dedup sets the worker's dedup function */
void worker_set_dedup(worker_ctx *ctx, int enable);

/* worker_set_reorder sets the worker's reorder function */
void worker_set_reorder(worker_ctx *ctx, int enable, uint16_t count, uint16_t offset);

/* worker_set_drop sets the worker's drop function */
void worker_set_drop(worker_ctx *ctx, int enable, int drop_count);

/* worker_destroy_ctx releases the memory of worker_ctx after use */
void worker_destroy_ctx(worker_ctx *ctx);

// RW fine tuning setting
void worker_set_tcp(worker_ctx *ctx, int enable, int burst_wnd, int rtt, float threshold, float pace);

#endif //HANDOFF_WORKER_H

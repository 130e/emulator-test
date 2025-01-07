#ifndef HANDOFF_ACTION_H
#define HANDOFF_ACTION_H

#include "nfqueue.h"
#include "worker.h"

#define ACTION_MAX_NFQUEUE (0xFF)

typedef struct {
    int mark; // 1,2 rf,mmw
    int hist_rw;
    int rtt;
} link_parameter;

typedef struct {
    uint64_t fire;
    worker_ctx *wkctx;
    int mark;
    int sample_interval;
    int burst_sample_interval;
    float threshold;
    float pace;
    int enable;
    link_parameter hist_param[3]; // save the heuristics
} tcp_ctx;

typedef struct {
    nfq_ctx **queues;
    worker_ctx **workers;
    tcp_ctx *tcp_sched;
} action_ctx;

/* action_init_ctx initializes action_ctx before use */
void action_init_ctx(action_ctx *ctx);

/* action_destroy_ctx releases the memory of action_ctx after use */
void action_destroy_ctx(action_ctx *ctx);

// tcp scheduler
void init_tcp_scheduler(tcp_ctx *ctx, action_ctx *action);

void tcp_schedule(void *);

uint64_t get_tcp_scheduler_fire(tcp_ctx *tctx);

/* Following are actions to be executed by the scheduler */

typedef struct {
    unsigned int time_ms;
} action_sleep_args;

void action_sleep(void *);

typedef struct {
    const char *command;
} action_command_args;

void action_command(void *);

typedef struct {
    action_ctx *ctx;
    uint16_t queue_num;
} action_init_nfqueue_args;

void action_init_nfqueue(void *);

typedef struct {
    action_ctx *ctx;
    uint16_t queue_num;
} action_start_nfqueue_args;

void action_start_nfqueue(void *);

typedef struct {
    action_ctx *ctx;
    uint16_t queue_num;
    uint32_t mark;
} action_set_mark_args;

void action_set_mark(void *);

typedef struct {
    action_ctx *ctx;
    uint16_t queue_num;
    uint32_t mark;
} action_sol_update_args;

void action_sol_update(void *);

typedef struct {
    action_ctx *ctx;
    int force_wnd;
    uint16_t queue_num;
    uint16_t rwnd;
} action_set_rwnd_args;

void action_set_rwnd(void *); // for zeroing the rw

typedef struct {
    action_ctx *ctx;
    uint64_t start_time;
    uint16_t queue_num;
    int enable;
    float threshold;
    float pace;
} action_set_adapt_args;

void action_set_adapt(void *);

typedef struct {
    action_ctx *ctx;
    uint16_t queue_num;
    int enable;
} action_set_dedup_args;

void action_set_dedup(void *);

typedef struct {
    action_ctx *ctx;
    uint16_t queue_num;
    int enable;
} action_set_burst_args;

void action_set_burst(void *);

typedef struct {
    action_ctx *ctx;
    uint16_t queue_num;
    int enable;
    uint16_t count;
    uint16_t offset;
} action_set_reorder_args;

void action_set_reorder(void *);

typedef struct {
    action_ctx *ctx;
    uint16_t queue_num;
    int enable;
    int sample_interval;
    float threshold;
    float pace;
    int fire;
    int mark;
    link_parameter init_param[3];
} action_init_tcp_sched_args;

void action_init_tcp_sched(void *);

typedef struct {
    action_ctx *ctx;
    uint16_t queue_num;
    int enable;
    int drop_count;
} action_set_drop_args;

void action_set_drop(void *);

typedef struct {
    action_ctx *ctx;
    uint16_t queue_num;
} action_stop_nfqueue_args;

void action_stop_nfqueue(void *);

typedef struct {
    action_ctx *ctx;
    uint16_t queue_num;
} action_teardown_nfqueue_args;

void action_teardown_nfqueue(void *);

#endif //HANDOFF_ACTION_H

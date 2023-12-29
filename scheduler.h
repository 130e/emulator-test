#ifndef HANDOFF_SCHEDULER_H
#define HANDOFF_SCHEDULER_H

#include <time.h>

#include "action.h"

#define SCHEDULER_MAX_EVENT (0xFFFF)
#define SCHEDULER_TICK_INTERVAL_US (10000)

typedef void (*scheduler_handler)(void *data);

typedef struct {
    uint64_t time_ms;
    scheduler_handler h;
    void *data;
    int idx; // for stable sorting
} scheduler_event;

typedef struct {
    const char *id;
    scheduler_event *events;
    int event_count;
} scheduler_ctx;

/* scheduler_init_ctx initializes scheduler_ctx before use */
void scheduler_init_ctx(scheduler_ctx *ctx, const char *id);

/* scheduler_add_event adds an event to the scheduler */
int scheduler_add_event(scheduler_ctx *ctx, uint64_t time_ms, scheduler_handler h, void *data);

/* scheduler_run starts the scheduler */
void scheduler_run(scheduler_ctx *ctx, tcp_ctx *tcp_sched);

/* scheduler_destroy_ctx releases the memory of scheduler_ctx after use */
void scheduler_destroy_ctx(scheduler_ctx *ctx);

#endif //HANDOFF_SCHEDULER_H

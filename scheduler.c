#include <stdlib.h>
#include <stdint.h>
#include <unistd.h>

#include "scheduler.h"
#include "log.h"

void scheduler_init_ctx(scheduler_ctx *ctx, const char *id) {
    if (id == NULL) id = "unnamed";
    log_debug("initializing scheduler context %s", id);
    ctx->id = id;
    ctx->events = malloc(sizeof(scheduler_event) * SCHEDULER_MAX_EVENT);
    ctx->event_count = 0;
}

int scheduler_add_event(scheduler_ctx *ctx, uint64_t time, scheduler_handler h, void *data) {
    log_debug("adding event at %ld to scheduler context %s", time, ctx->id);
    if (ctx->event_count >= SCHEDULER_MAX_EVENT) {
        log_error("scheduler context %s has too many events", ctx->id);
        return -1;
    }
    ctx->events[ctx->event_count].time_ms = time;
    ctx->events[ctx->event_count].h = h;
    ctx->events[ctx->event_count].data = data;
    ctx->events[ctx->event_count].idx = ctx->event_count;
    ctx->event_count++;
    return 0;
}

int scheduler_compare_event(const void *a, const void *b) {
    if (((scheduler_event *) a)->time_ms > ((scheduler_event *) b)->time_ms) {
        return 1;
    } else if (((scheduler_event *) a)->time_ms < ((scheduler_event *) b)->time_ms) {
        return -1;
    } else if (((scheduler_event *) a)->idx > ((scheduler_event *) b)->idx) {
        return 1;
    } else if (((scheduler_event *) a)->idx < ((scheduler_event *) b)->idx) {
        return -1;
    }
    return 0;
}

uint64_t scheduler_get_time_ms() {
    struct timespec now;
    clock_gettime(CLOCK_MONOTONIC, &now);
    return now.tv_sec * 1000 + now.tv_nsec / 1000000;
}

void scheduler_run(scheduler_ctx *ctx, tcp_ctx *tcp_sched) {
    log_info("starting scheduler %s with %d event(s)", ctx->id, ctx->event_count);
    if (ctx->event_count <= 0) {
        return;
    }
    qsort(ctx->events, ctx->event_count, sizeof(scheduler_event), scheduler_compare_event);
    uint64_t started_at = scheduler_get_time_ms();
    int i = 0;

    // the last event must be nfq teardown
    while (i < ctx->event_count) {
        uint64_t fire = tcp_sched->fire + tcp_sched->sample_interval;
        scheduler_handler event_handler = tcp_schedule;
        void *data = tcp_sched;
        if (ctx->events[i].time_ms < fire) {
            fire = ctx->events[i].time_ms;
            event_handler = ctx->events[i].h;
            data = ctx->events[i].data;
            i++;
            log_trace("scheduler %s: executing event %d at %ld ms", ctx->id, i, (long)fire);
        }
        else {
            tcp_sched->fire += tcp_sched->sample_interval;
        }
        while (scheduler_get_time_ms() - started_at < fire) {
            usleep(SCHEDULER_TICK_INTERVAL_US);
        }
        event_handler(data);
        log_debug("scheduler %s: Finish executing event %d at %ld ms", ctx->id, i, (long)fire);
    }

    log_info("All tasks in scheduler %s finished", ctx->id);
}

void scheduler_destroy_ctx(scheduler_ctx *ctx) {
    log_debug("destroying scheduler context %s", ctx->id);
    free(ctx->events);
}

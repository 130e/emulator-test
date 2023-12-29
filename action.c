#include <errno.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "action.h"
#include "nfqueue.h"
#include "log.h"

#define RWSCALE 10

void action_init_ctx(action_ctx *ctx) {
    ctx->queues = (nfq_ctx **) malloc(sizeof(nfq_ctx *) * ACTION_MAX_NFQUEUE);
    ctx->workers = (worker_ctx **) malloc(sizeof(worker_ctx *) * ACTION_MAX_NFQUEUE);
}

void init_tcp_scheduler(tcp_ctx *ctx, action_ctx *action) {
    action->tcp_sched = ctx;
    ctx->fire = 0xFFFFFFFF;
    ctx->wkctx = NULL;
    ctx->sample_interval = 0;
}

void tcp_schedule(void *data) {
    // assume ctx initialized
    tcp_ctx *tctx = (tcp_ctx*)data;
    worker_ctx *ctx = tctx->wkctx;
    int mark = ctx->mark;
    // should be able to handle 3 types of behavior, 0, burst, passive
    pthread_mutex_lock(&ctx->rwnd_lock);
    // burst
    if (ctx->do_burst) {
        // sample and cal burst as ctx->tune_rwnd
        double rate = ((double)tctx->hist_param[tctx->mark].rtt / (double)tctx->sample_interval);
        uint64_t rw_est = (int)(ctx->data_rcvd * rate);
        rw_est >>= RWSCALE;
        if (rw_est > ctx->tune_rwnd) {
            ctx->tune_rwnd = rw_est;
            log_debug("Burst overwritten %d %f", ctx->tune_rwnd, rate);
        }
    }
    else if (ctx->do_adapt) {
        uint64_t cw = (ctx->data_rcvd >> RWSCALE); // scale by rw factor
        if (ctx->tune_rwnd > 0) {
            double rate = ((double)cw / (double)ctx->tune_rwnd);
            if (rate > 1) {
                cw = ctx->tune_rwnd;
            }
            /*log_fatal("%d %d %d", tctx->fire, cw, ctx->tune_rwnd);*/
            /*uint64_t hist_rw = tctx->hist_param[tctx->mark].hist_rw;*/
            /*double hist_diff;*/
            /*if (hist_rw > ctx->tune_rwnd)*/
                /*hist_diff = (hist_rw - ctx->tune_rwnd) / ctx->tune_rwnd;*/
            /*else {*/
                /*hist_diff = (ctx->tune_rwnd - hist_rw) / ctx->tune_rwnd;*/
            /*}*/
            if (rate > tctx->threshold) {
                // increment
                /*if (ctx->tune_rwnd > hist_rw)*/
                    /*hist_diff = 0;*/
                ctx->tune_rwnd = ctx->tune_rwnd * (1 + tctx->pace );
            }
            else if (rate < 0.7) {
                /*if (ctx->tune_rwnd < hist_rw)*/
                    /*hist_diff = 0;*/
                ctx->tune_rwnd = ctx->tune_rwnd * (1 - tctx->pace/4 );
            }
            /*log_fatal("%d %ld %lf", tctx->fire, cw, rate);*/
        }
        /*log_fatal("%ld %ld %ld %ld", tctx->fire, ctx->rwnd, ctx->data_rcvd, cw);*/
    }
    /*log_fatal("sched %d %d %d", ctx->tune_rwnd, ctx->hist_param[1].hist_rw, ctx->hist_param[2].hist_rw);*/
    // if nothing is set, means no burst, passive, so 0 wnd
    ctx->data_rcvd = 0;
    /*tctx->fire += ctx->link_param[mark].rtt;*/
    pthread_mutex_unlock(&ctx->rwnd_lock);
}

uint64_t get_tcp_scheduler_fire(tcp_ctx *tctx) {
    return tctx->fire + tctx->sample_interval;
}

void action_sleep(void *data) {
    unsigned int time_ms = ((action_sleep_args *) data)->time_ms;
    log_debug("start sleeping %u", time_ms);
    usleep(time_ms * 1000);
}

void action_command(void *data) {
    const char *command = ((action_command_args *) data)->command;
    log_debug("start executing command: %s", command);
    system(command);
}

void action_init_nfqueue(void *data) {
    action_init_nfqueue_args *args = (action_init_nfqueue_args *) data;
    nfq_ctx *qctx = malloc(sizeof(nfq_ctx));
    worker_ctx *wctx = malloc(sizeof(worker_ctx));
    worker_init_ctx(wctx, "");
    if (nfq_init(qctx, args->queue_num, worker_callback, wctx)) {
        log_error("failed to initialize nfqueue %d: %s", args->queue_num, strerror(errno));
        return;
    }
    args->ctx->queues[args->queue_num] = qctx;
    args->ctx->workers[args->queue_num] = wctx;
    log_debug("initialized nfqueue %d", args->queue_num);
}

void action_start_nfqueue(void *data) {
    action_start_nfqueue_args *args = (action_start_nfqueue_args *) data;
    nfq_ctx *qctx = args->ctx->queues[args->queue_num];
    nfq_start(qctx);
    log_debug("started nfqueue %d", args->queue_num);
}

void action_stop_nfqueue(void *data) {
    action_stop_nfqueue_args *args = (action_stop_nfqueue_args *) data;
    nfq_ctx *qctx = args->ctx->queues[args->queue_num];
    nfq_stop(qctx);
    log_debug("stopped nfqueue %d", args->queue_num);
}

void action_teardown_nfqueue(void *data) {
    action_teardown_nfqueue_args *args = (action_teardown_nfqueue_args *) data;
    nfq_ctx *qctx = args->ctx->queues[args->queue_num];
    worker_ctx *wctx = args->ctx->workers[args->queue_num];
    if (nfq_teardown(qctx)) {
        log_error("failed to teardown nfqueue %d: %s", args->queue_num, strerror(errno));
        return;
    }
    worker_destroy_ctx(wctx);
    args->ctx->queues[args->queue_num] = NULL;
    args->ctx->workers[args->queue_num] = NULL;
    log_debug("tore down nfqueue %d", args->queue_num);
}

void action_destroy_ctx(action_ctx *ctx) {
    free(ctx->queues);
    free(ctx->workers);
}

void action_set_mark(void *data) {
    action_set_mark_args *args = (action_set_mark_args *) data;
    worker_ctx *wctx = args->ctx->workers[args->queue_num];
    worker_set_mark(wctx, args->mark);
    log_debug("set mark %d for nfqueue %d", args->mark, args->queue_num);
}

void action_sol_update(void *data) {
    action_sol_update_args *args = (action_sol_update_args*) data;
    worker_ctx *wctx = args->ctx->workers[args->queue_num];
    tcp_ctx *tctx = args->ctx->tcp_sched;
    if (wctx->tune_rwnd > 0) {
        tctx->hist_param[tctx->mark].hist_rw = wctx->tune_rwnd;
        tctx->mark = args->mark;
    }
    worker_sol_update(wctx, tctx->hist_param[args->mark].hist_rw);
    log_debug("set mark %d for nfqueue %d", args->mark, args->queue_num);
}

void action_set_reorder(void *data) {
    action_set_reorder_args *args = (action_set_reorder_args *) data;
    worker_ctx *wctx = args->ctx->workers[args->queue_num];
    worker_set_reorder(wctx, args->enable, args->count, args->offset);
    log_debug("set reorder %d for nfqueue %d", args->enable, args->queue_num);
}

void action_set_drop(void *data) {
    action_set_drop_args *args = (action_set_drop_args *) data;
    worker_ctx *wctx = args->ctx->workers[args->queue_num];
    worker_set_drop(wctx, args->enable, args->drop_count);
    log_debug("set drop %d for nfqueue %d", args->enable, args->queue_num);
}

void action_set_rwnd(void *data) {
    action_set_rwnd_args *args = (action_set_rwnd_args *) data;
    worker_ctx *wctx = args->ctx->workers[args->queue_num];
    uint32_t rwnd = args->rwnd;
    if (rwnd < 10) { // use lte hist rw
        tcp_ctx *tctx = args->ctx->tcp_sched;
        /*rwnd = tctx->hist_param[1].hist_rw / 4;*/
        rwnd = 10;
    }
    worker_set_rwnd(wctx, rwnd);
    log_debug("set rwnd %d for nfqueue %d", args->rwnd, args->queue_num);
}

void action_set_dedup(void *data) {
    action_set_dedup_args *args = (action_set_dedup_args *) data;
    worker_ctx *wctx = args->ctx->workers[args->queue_num];
    worker_set_dedup(wctx, args->enable);
    log_debug("set dedup %d for nfqueue %d", args->enable, args->queue_num);
}

void action_set_burst(void *data) {
    action_set_burst_args *args = (action_set_burst_args *) data;
    worker_ctx *wctx = args->ctx->workers[args->queue_num];
    tcp_ctx *tctx = args->ctx->tcp_sched;
    worker_set_burst(wctx, args->enable, tctx->hist_param[tctx->mark].hist_rw);
    if (args->enable > 0) {
        tctx->sample_interval = tctx->burst_sample_interval;
        /*wctx->tune_rwnd = tctx->hist_param[tctx->mark].hist_rw;*/
    }
    else {
        // mark down
        if (wctx->tune_rwnd > tctx->hist_param[tctx->mark].hist_rw) {
            tctx->hist_param[tctx->mark].hist_rw = wctx->tune_rwnd;
        }
    }
    log_debug("reset rwnd %d for nfqueue %d", 0, args->queue_num);
}

void action_set_adapt(void *data) {
    action_set_adapt_args *args = (action_set_adapt_args *) data;
    log_debug("Set adapt %d for nfqueue %d", args->enable, args->queue_num);
    worker_ctx *wctx = args->ctx->workers[args->queue_num];
    tcp_ctx *tctx = args->ctx->tcp_sched;
    if (args->enable > 0) {
        tctx->sample_interval = tctx->hist_param[tctx->mark].rtt;
    }
    worker_set_adapt(wctx, args->enable, tctx->hist_param[tctx->mark].hist_rw);
}

void action_init_tcp_sched(void *data) {
    action_init_tcp_sched_args *args = (action_init_tcp_sched_args *) data;
    worker_ctx *wctx = args->ctx->workers[args->queue_num];
    tcp_ctx *tctx = args->ctx->tcp_sched;
    tctx->wkctx = wctx; // link wkctx to tcp solution
    tctx->fire = args->fire;
    tctx->burst_sample_interval = args->sample_interval;
    tctx->threshold = args->threshold;
    tctx->pace = args->pace;
    tctx->mark = args->mark;
    tctx->sample_interval = args->init_param[args->mark].rtt;
    tctx->enable = args->enable;
    for (int i=1; i<3; i++) {
        tctx->hist_param[i].mark = i;
        tctx->hist_param[i].hist_rw = args->init_param[i].hist_rw;
        tctx->hist_param[i].rtt = args->init_param[i].rtt;
        log_debug("init tcp %d", tctx->hist_param[i].hist_rw);
    }
    worker_init_tcp_sched(wctx, args->enable);
    worker_set_rwnd(wctx, tctx->hist_param[tctx->mark].hist_rw);
    log_debug("Init TCP sched %d for nfqueue %d", args->enable, args->queue_num);
}

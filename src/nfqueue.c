#include <errno.h>
#include <pthread.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>

#include "nfqueue.h"
#include "log.h"

enum nfq_status {
    NFQ_STOPPED = 0,
    NFQ_RUNNING,
    NFQ_DEAD,
};

void *nfq_run(void *);

int nfq_init(nfq_ctx *ctx, uint16_t queue_num, nfq_callback *cb, void *data) {
    log_debug("initializing nfqueue %hu", queue_num);
    ctx->h = nfq_open();
    if (!ctx->h) {
        log_error("failed to open nfq: %s (%d)", strerror(errno), errno);
        return -1;
    }
    unsigned int n;
    if ((n = nfnl_rcvbufsiz(nfq_nfnlh(ctx->h), NFQ_QUEUE_SIZE * NFQ_PKT_SIZE)) < NFQ_QUEUE_SIZE * NFQ_PKT_SIZE) {
        log_warn("requested queue size %u, get %u", NFQ_QUEUE_SIZE * NFQ_PKT_SIZE, n);
        return -1;
    }
    ctx->qh = nfq_create_queue(ctx->h, queue_num, cb, data);
    if (!ctx->qh) {
        log_error("failed to create nfq: %s (%d)", strerror(errno), errno);
        return -1;
    }
    if (nfq_set_mode(ctx->qh, NFQNL_COPY_PACKET, NFQ_PKT_SIZE) < 0) {
        log_error("failed to set nfq mode: %s (%d)", strerror(errno), errno);
        return -1;
    }
    if (nfq_set_queue_maxlen(ctx->qh, NFQ_QUEUE_SIZE) < 0) {
        log_error("failed to set nfq queue max length: %s (%d)", strerror(errno), errno);
        return -1;
    }
    ctx->queue_num = queue_num;
    ctx->fd = nfq_fd(ctx->h);
    pthread_t nfq_thread;
    if (pthread_create(&nfq_thread, NULL, nfq_run, ctx) != 0) {
        log_error("failed to create nfq thread: %s (%d)", strerror(errno), errno);
        return -1;
    }
    return 0;
}

void nfq_start(nfq_ctx *ctx) {
    __atomic_store_n(&ctx->status, NFQ_RUNNING, __ATOMIC_SEQ_CST);
    log_debug("nfqueue %hu started", ctx->queue_num);
}

void nfq_stop(nfq_ctx *ctx) {
    __atomic_store_n(&ctx->status, NFQ_STOPPED, __ATOMIC_SEQ_CST);
    log_debug("nfqueue %hu stopped", ctx->queue_num);
}

int nfq_teardown(nfq_ctx *ctx) {
    log_debug("tearing down nfqueue %hu", ctx->queue_num);
    int ret = 0;
    __atomic_store_n(&ctx->status, NFQ_DEAD, __ATOMIC_SEQ_CST);
    if (nfq_destroy_queue(ctx->qh)) {
        log_error("failed to destroy nfq queue: %s (%d)", strerror(errno), errno);
        ret = -1;
    }
    if (nfq_close(ctx->h)) {
        log_error("failed to close nfq connection: %s (%d)", strerror(errno), errno);
        ret = -1;
    }
    return ret;
}

void *nfq_run(void *data) {
    int n;
    char buf[NFQ_PKT_SIZE];
    nfq_ctx *ctx = (nfq_ctx *) data;
    log_debug("starting nfq loop for queue %hu", ctx->queue_num);
    while (1) {
        switch (__atomic_load_n(&ctx->status, __ATOMIC_SEQ_CST)) {
            case NFQ_RUNNING:
                break;
            case NFQ_STOPPED:
                usleep(1000);
                continue;
            case NFQ_DEAD:
                log_debug("stopping nfq thread for queue %hu", ctx->queue_num);
                return NULL;
        }
        if ((n = recv(ctx->fd, buf, sizeof(buf), 0)) < 0) {
            log_error("error during receiving packet for queue %hu: %s (%d)", ctx->queue_num, strerror(errno), errno);
            continue;
        }
        if (nfq_handle_packet(ctx->h, buf, n)) {
            log_error("error during handling packet from queue %hu: %s (%d)", ctx->queue_num, strerror(errno), errno);
            continue;
        }
    }
}

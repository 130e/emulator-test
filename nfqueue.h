#ifndef HANDOFF_NFQUEUE_H
#define HANDOFF_NFQUEUE_H

#include <stdint.h>
#include <libnetfilter_queue/libnetfilter_queue.h>

#define NFQ_QUEUE_SIZE (4096)
#define NFQ_PKT_SIZE (0xFFFF)

typedef struct {
    uint16_t queue_num;
    struct nfq_handle *h;
    struct nfq_q_handle *qh;
    int fd;
    int status;
} nfq_ctx;

/*
 * nfq_init creates a session to consume an NFQUEUE.
 *
 * - ctx: an "nfq_ctx" struct for holding the internal data
 * - queue_num: the NFQUEUE number
 * - cb: the callback function
 * - data: anything to be passed into the callback function
 */
int nfq_init(nfq_ctx *ctx, uint16_t queue_num, nfq_callback *cb, void *data);

/* nfq_start starts consuming the packets in the queue */
void nfq_start(nfq_ctx *ctx);

/* nfq_stop stops consuming the packets in the queue */
void nfq_stop(nfq_ctx *ctx);

/* nfq_teardown closes the queue */
int nfq_teardown(nfq_ctx *ctx);

#endif //HANDOFF_NFQUEUE_H

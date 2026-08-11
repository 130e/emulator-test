#ifndef HANDOFF_NFQUEUE_H
#define HANDOFF_NFQUEUE_H

#include <libnetfilter_queue/libnetfilter_queue.h>
#include <stdint.h>

/* NFQ_QUEUE_SIZE is the max number of packets the kernel holds in the queue. */
#define NFQ_QUEUE_SIZE (4096)

/*
 * NFQ_PKT_SIZE is the number of bytes the kernel copies per packet (the
 * nfq_set_mode copy range), and the per-packet unit used to size the netlink
 * socket receive buffer. It must be >= the link MTU; 1600 covers an MTU of
 * 1500. Raising it also raises the receive buffer request, which is capped by
 * net.core.rmem_max (see nfq_init).
 */
#define NFQ_PKT_SIZE (1600)

/*
 * NFQ_MSG_BUF is the size of the userspace recv() buffer for a single netlink
 * message. A message is the copied packet plus the nfnetlink header and its
 * attributes (~60 bytes), so this must be strictly larger than NFQ_PKT_SIZE.
 * It is a stack allocation in the queue thread and costs nothing, so it is
 * kept generous on purpose: a buffer too small truncates the message, which
 * makes nfq_handle_packet fail, which means no verdict is ever issued for that
 * packet and the queue silently backs up.
 */
#define NFQ_MSG_BUF (65536)

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

#endif // HANDOFF_NFQUEUE_H

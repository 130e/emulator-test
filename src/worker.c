#include <stdbool.h>
#include <stddef.h>
#include <arpa/inet.h>
#include <stdlib.h>
#include <libnetfilter_queue/libnetfilter_queue.h>
#include <libnetfilter_queue/libnetfilter_queue_ipv4.h>
#include <libnetfilter_queue/libnetfilter_queue_tcp.h>
#include <libnetfilter_queue/pktbuff.h>
#include <linux/ip.h>
#include <linux/tcp.h>
#include <linux/netfilter.h>

#include "worker.h"
#include "log.h"

// Debugging
int packet_logging(struct nfq_data *nfa) {
    int handled = 0;

    struct timespec now;
    clock_gettime(CLOCK_REALTIME, &now);
    uint64_t ts = now.tv_sec * 1000 + now.tv_nsec / 1000000;

    unsigned char *nf_packet;
    int len = nfq_get_payload(nfa, &nf_packet);
    if (len < sizeof(struct iphdr))
        goto done;
    struct iphdr *iph = ((struct iphdr *) nf_packet);
    if (len < (iph->ihl << 2) + sizeof(struct tcphdr))
        goto done;
    if (iph->saddr == inet_addr("10.0.0.1")) {
        struct tcphdr *tcph = ((struct tcphdr *) (nf_packet + (iph->ihl << 2)));
        uint32_t seq = ntohl(tcph->seq);
        uint32_t ack = ntohl(tcph->ack_seq);
        log_fatal("packet,%llu,%u,%lu,%lu", ts, ntohs(tcph->source), seq, ack);
    }
    done:
    return handled;
}

int worker_handle_drop(worker_ctx *ctx, int *ret, struct nfq_q_handle *qh, u_int32_t id);

int worker_handle_reorder(worker_ctx *ctx, int *ret, struct nfq_q_handle *qh, u_int32_t id);

int worker_handle_dedup(worker_ctx *ctx, int *ret, struct nfq_q_handle *qh, u_int32_t id, struct nfq_data *nfa);

int worker_handle_rwnd(worker_ctx *ctx, int *ret, struct nfq_q_handle *qh, u_int32_t id, struct nfq_data *nfa);

int worker_callback(struct nfq_q_handle *qh, struct nfgenmsg *nfmsg, struct nfq_data *nfa, void *data) {
    worker_ctx *ctx = (worker_ctx *) data;
    u_int32_t id;
    struct nfqnl_msg_packet_hdr *ph;
    ph = nfq_get_msg_packet_hdr(nfa);
    id = ntohl(ph->packet_id);
    int ret;
    packet_logging(nfa);
    // handle drop
    if (worker_handle_drop(ctx, &ret, qh, id)) return ret;
    // handle reorder
    if (worker_handle_reorder(ctx, &ret, qh, id)) return ret;
    // handle dedup
    if (worker_handle_dedup(ctx, &ret, qh, id, nfa)) return ret;
    // handle rwnd and update last_ack always
    if (worker_handle_rwnd(ctx, &ret, qh, id, nfa)) return ret;
    return nfq_set_verdict2(qh, id, NF_ACCEPT, __atomic_load_n(&ctx->mark, __ATOMIC_SEQ_CST), 0, NULL);
}

int worker_handle_drop(worker_ctx *ctx, int *ret, struct nfq_q_handle *qh, u_int32_t id) {
    int handled = 0;
    pthread_mutex_lock(&ctx->drop_lock);
    if (ctx->do_drop) {
        if (ctx->drop_count-- > 0) {
            // should drop
            log_trace("drop packet %u", id);
            *ret = nfq_set_verdict(qh, id, NF_DROP, 0, NULL);
            handled = 1;
        }
        if (ctx->drop_count <= 0) ctx->do_drop = 0;
    }
    pthread_mutex_unlock(&ctx->drop_lock);
    return handled;
}

int worker_handle_reorder(worker_ctx *ctx, int *ret, struct nfq_q_handle *qh, u_int32_t id) {
    int handled = 0;
    pthread_mutex_lock(&ctx->reorder_lock);
    if (ctx->do_reorder) {
        if (ctx->reorder_count-- > 0) {
            // queue the packet
            ctx->reorder_ids[ctx->reorder_id_cur++] = id;
            log_trace("queued packet %u", id);
        } else if (ctx->reorder_offset-- > 0) {
            // wait for the offset
            *ret = nfq_set_verdict2(qh, id, NF_ACCEPT, __atomic_load_n(&ctx->mark, __ATOMIC_SEQ_CST), 0, NULL);
            log_trace("passed offset packet %u", id);
        }
        if (ctx->reorder_offset <= 0) {
            // release the queued packets
            for (int i = ctx->reorder_id_cur - 1; i >= 0; i--) {
                *ret = nfq_set_verdict2(qh, ctx->reorder_ids[i], NF_ACCEPT, __atomic_load_n(&ctx->mark, __ATOMIC_SEQ_CST), 0,
                                 NULL);
                log_trace("released queued packet %u", ctx->reorder_ids[i]);
            }
            ctx->do_reorder = 0;
            ctx->reorder_id_cur = 0;
        }
        handled = 1;
    }
    pthread_mutex_unlock(&ctx->reorder_lock);
    return handled;
}

int worker_handle_dedup(worker_ctx *ctx, int *ret, struct nfq_q_handle *qh, u_int32_t id, struct nfq_data *nfa) {
    int handled = 0;
    pthread_mutex_lock(&ctx->dedup_lock);
    if (ctx->do_dedup) {
        unsigned char *nf_packet;
        int len = nfq_get_payload(nfa, &nf_packet);
        if (len < sizeof(struct iphdr))
            goto done;
        struct iphdr *iph = ((struct iphdr *) nf_packet);
        if (len < (iph->ihl << 2) + sizeof(struct tcphdr))
            goto done;
        struct tcphdr *tcph = ((struct tcphdr *) (nf_packet + (iph->ihl << 2)));
        uint32_t ack = ntohl(tcph->ack_seq);
        if ((ack == ctx->last_ack) && (len <= (iph->ihl << 2) + (tcph->doff << 2))) {
            // drop ack-only packets
            *ret = nfq_set_verdict(qh, id, NF_DROP, 0, NULL);
            log_trace("dropped dup ack %u", id);
            // add a fatal log here for a clean log detail
            log_fatal("%u", ack);
            handled = 1;
        }
    }
    done:
    pthread_mutex_unlock(&ctx->dedup_lock);
    return handled;
}

int worker_handle_rwnd(worker_ctx *ctx, int *ret, struct nfq_q_handle *qh, u_int32_t id, struct nfq_data *nfa) {
    int handled = 0;
    pthread_mutex_lock(&ctx->rwnd_lock);
    unsigned char *nf_packet;
    int len = nfq_get_payload(nfa, &nf_packet);
    if (len < sizeof(struct iphdr))
        goto done;
    struct iphdr *iph = ((struct iphdr *) nf_packet);
    if (iph->protocol != IPPROTO_TCP || len < (iph->ihl << 2) + sizeof(struct tcphdr))
        goto done;
    struct pkt_buff *pkBuff = pktb_alloc(AF_INET, nf_packet, len, 0x1000);
    iph = nfq_ip_get_hdr(pkBuff);
    nfq_ip_set_transport_header(pkBuff, iph);
    struct tcphdr *tcph = nfq_tcp_get_hdr(pkBuff);

    if (ctx->do_rwnd) {
        // update data rcvd
        uint32_t recv = ntohl(tcph->ack_seq) - ctx->last_ack;
        /*log_fatal("worker %d", ctx->tune_rwnd);*/
        if (recv < 0)
            log_error("Unexpected ack - last_ack value < 0");
        ctx->data_rcvd += recv;

        // set rwnd
        uint16_t original_rwnd = ntohs(tcph->window);
        /*log_error("%d", ctx->data_rcvd);*/
        /*log_fatal("%u %u", original_rwnd, ctx->tune_rwnd);*/
        if (ctx->tune_rwnd < original_rwnd) {
            log_trace("%u %u", (unsigned short)original_rwnd, (unsigned short)ctx->tune_rwnd);
            tcph->window = htons(ctx->tune_rwnd);
            nfq_tcp_compute_checksum_ipv4(tcph, iph);
        }

        *ret = nfq_set_verdict2(qh, id, NF_ACCEPT, __atomic_load_n(&ctx->mark, __ATOMIC_SEQ_CST), pktb_len(pkBuff), pktb_data(pkBuff));
        pktb_free(pkBuff);
        log_trace("set rwnd %hu for packet %u", ctx->tune_rwnd, id);
        handled = 1;
        /*log_fatal("%hu %u", ctx->tune_rwnd, ctx->data_rcvd);*/
    }
    done:
    // update last_ack
    ctx->last_ack = ntohl(tcph->ack_seq);

    pthread_mutex_unlock(&ctx->rwnd_lock);
    return handled;
}

void worker_init_ctx(worker_ctx *ctx, const char *id) {
    if (id == NULL) id = "unnamed";
    log_debug("initializing worker context %s", id);
    ctx->id = id;
    ctx->mark = 0;
    ctx->do_rwnd = 0;
    ctx->do_dedup = 0;
    ctx->do_reorder = 0;
    ctx->do_drop = 0;
    ctx->do_adapt = 0;
    ctx->do_burst = 0;
    ctx->reorder_ids = malloc(sizeof(uint32_t) * WORKER_MAX_REORDER_COUNT);
    pthread_mutex_init(&ctx->rwnd_lock, NULL);
    pthread_mutex_init(&ctx->reorder_lock, NULL);
    pthread_mutex_init(&ctx->dedup_lock, NULL);
    pthread_mutex_init(&ctx->drop_lock, NULL);
}

void worker_destroy_ctx(worker_ctx *ctx) {
    log_debug("destroying worker context %s", ctx->id);
    free(ctx->reorder_ids);
    pthread_mutex_destroy(&ctx->rwnd_lock);
    pthread_mutex_destroy(&ctx->reorder_lock);
    pthread_mutex_destroy(&ctx->dedup_lock);
    pthread_mutex_destroy(&ctx->drop_lock);
}

void worker_set_mark(worker_ctx *ctx, uint32_t mark) {
    __atomic_store_n(&ctx->mark, mark, __ATOMIC_SEQ_CST);
    log_debug("worker %s now setting mark %u", ctx->id, mark);
}

void worker_sol_update(worker_ctx *ctx, int rwnd) {
    pthread_mutex_lock(&ctx->rwnd_lock);
    ctx->do_adapt = 0;
    ctx->do_burst = 0;
    ctx->tune_rwnd = rwnd;
    pthread_mutex_unlock(&ctx->rwnd_lock);
}

void worker_set_rwnd(worker_ctx *ctx, uint16_t rwnd) {
    pthread_mutex_lock(&ctx->rwnd_lock);
    ctx->tune_rwnd = rwnd;
    pthread_mutex_unlock(&ctx->rwnd_lock);
}

void worker_set_burst(worker_ctx *ctx, int enable, int rwnd) {
    pthread_mutex_lock(&ctx->rwnd_lock);
    ctx->do_burst = enable;
    if (enable > 0) {
        ctx->do_adapt = 0; // stop adapting when force wnd
        ctx->data_rcvd = 0;
        ctx->tune_rwnd = rwnd;
        log_debug("Burst worker %s now setting rwnd %hu", ctx->id, ctx->tune_rwnd);
    }
    pthread_mutex_unlock(&ctx->rwnd_lock);
}

void worker_set_adapt(worker_ctx *ctx, int enable, int rwnd) {
    // changing param for tcp scheduler
    pthread_mutex_lock(&ctx->rwnd_lock);
    ctx->do_adapt = enable;
    if (enable > 0) {
        ctx->do_burst = 0;
        ctx->data_rcvd = 0;
        ctx->tune_rwnd = rwnd;
        log_debug("Adapt worker %s now setting rwnd %hu", ctx->id, ctx->tune_rwnd);
    }
    pthread_mutex_unlock(&ctx->rwnd_lock);
}

void worker_init_tcp_sched(worker_ctx *ctx, int do_rwnd) {
    log_debug("worker %s init tcp sched", ctx->id);
    pthread_mutex_lock(&ctx->rwnd_lock);
    ctx->do_rwnd = do_rwnd;
    ctx->do_adapt = 1;
    ctx->data_rcvd = 0;
    pthread_mutex_unlock(&ctx->rwnd_lock);
}

void worker_set_dedup(worker_ctx *ctx, int enable) {
    pthread_mutex_lock(&ctx->dedup_lock);
    ctx->do_dedup = enable;
    if (enable) {
        log_debug("worker %s now dropping dup acks", ctx->id);
    } else {
        log_debug("worker %s now not dropping dup acks", ctx->id);
    }
    pthread_mutex_unlock(&ctx->dedup_lock);
}

void worker_set_reorder(worker_ctx *ctx, int enable, uint16_t count, uint16_t offset) {
    if (count > WORKER_MAX_REORDER_COUNT) {
        count = WORKER_MAX_REORDER_COUNT;
    }
    pthread_mutex_lock(&ctx->reorder_lock);
    ctx->do_reorder = enable;
    if (enable) {
        ctx->reorder_count = count;
        ctx->reorder_offset = offset;
        ctx->reorder_id_cur = 0;
        log_debug("worker %s now reordering %hu packets with offset %hu", ctx->id, count, offset);
    } else {
        log_debug("worker %s now not reordering", ctx->id);
    }
    pthread_mutex_unlock(&ctx->reorder_lock);
}

void worker_set_drop(worker_ctx *ctx, int enable, int drop_count) {
    pthread_mutex_lock(&ctx->drop_lock);
    ctx->do_drop = enable;
    if (enable) {
        ctx->drop_count = drop_count;
        log_debug("worker %s now dropping %d packets", ctx->id, drop_count);
    } else {
        log_debug("worker %s now not dropping packets", ctx->id);
    }
    pthread_mutex_unlock(&ctx->drop_lock);
}


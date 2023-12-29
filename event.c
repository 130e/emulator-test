#include <string.h>
#include <stdlib.h>

#include "event.h"
#include "log.h"

// event format: time_ms event_id data...

// cmd
int parse_cmd(scheduler_ctx *scheduler, int time_ms, char *data) {
    char *buf = malloc(strlen(data)+1);
    strcpy(buf, data);
    log_info("Run cmd %s", buf);
    action_command_args *args = malloc(sizeof(action_command_args));
    args->command = buf;
    return scheduler_add_event(scheduler, time_ms, action_command, args);
}

// queue_num new_mark gap reord_cnt reord_offset loss
int parse_ho(scheduler_ctx *scheduler, action_ctx *action, int time_ms, char *data) {
    // handle OUTQ
    char *tok = data;
    int queue_num = strtol(tok, NULL, 0);
    tok = strtok(NULL, ",");
    int mark = strtol(tok, NULL, 0);
    tok = strtok(NULL, ",");
    int gap_time = strtol(tok, NULL, 0);
    tok = strtok(NULL, ",");
    int reord_cnt = strtol(tok, NULL, 0);
    tok = strtok(NULL, ",");
    int reord_offset = strtol(tok, NULL, 0);
    tok = strtok(NULL, ",");
    int drop_cnt = strtol(tok, NULL, 0);

    action_stop_nfqueue_args *stop_args = malloc(sizeof(action_stop_nfqueue_args));
    stop_args->ctx = action;
    stop_args->queue_num = queue_num;
    scheduler_add_event(scheduler, time_ms, action_stop_nfqueue, stop_args);

    action_start_nfqueue_args *start_args = malloc(sizeof(action_start_nfqueue_args));
    start_args->ctx = action;
    start_args->queue_num = queue_num;
    scheduler_add_event(scheduler, time_ms + gap_time, action_start_nfqueue, start_args);

    action_set_mark_args *mark_args = malloc(sizeof(action_set_mark_args));
    mark_args->ctx = action;
    mark_args->queue_num = queue_num;
    mark_args->mark = mark;
    scheduler_add_event(scheduler, time_ms, action_set_mark, mark_args);

    if (drop_cnt > 0) {
        action_set_drop_args *drop_args = malloc(sizeof(action_set_drop_args));
        drop_args->ctx = action;
        drop_args->queue_num = queue_num;
        drop_args->enable = 1;
        drop_args->drop_count = drop_cnt;
        scheduler_add_event(scheduler, time_ms, action_set_drop, drop_args);
    }

    if (reord_cnt > 0) {
        action_set_reorder_args *reord_args = malloc(sizeof(action_set_reorder_args));
        reord_args->ctx = action;
        reord_args->queue_num = queue_num;
        reord_args->enable = 1;
        reord_args->count = reord_cnt;
        reord_args->offset = reord_offset;
        scheduler_add_event(scheduler, time_ms, action_set_reorder, reord_args);
    }

    return 0;
}

// data: queue_num mark end_ms
int parse_init(scheduler_ctx *scheduler, action_ctx *action, int time_ms, char *data) {
    char *tok = data;
    int queue_num = strtol(tok, NULL, 0);
    tok = strtok(NULL, ",");
    int mark = strtol(tok, NULL, 0);
    tok = strtok(NULL, ",");
    int end_ms = strtol(tok, NULL, 0);

    // TODO check if malloc are freed
    action_init_nfqueue_args *init_args = malloc(sizeof(action_init_nfqueue_args));
    init_args->ctx = action;
    init_args->queue_num = queue_num;
    scheduler_add_event(scheduler, time_ms, action_init_nfqueue, init_args);

    action_teardown_nfqueue_args *destroy_args = malloc(sizeof(action_start_nfqueue_args));
    destroy_args->ctx = action;
    destroy_args->queue_num = queue_num;
    scheduler_add_event(scheduler, end_ms, action_teardown_nfqueue, destroy_args);

    action_start_nfqueue_args *start_args = malloc(sizeof(action_start_nfqueue_args));
    start_args->ctx = action;
    start_args->queue_num = queue_num;
    scheduler_add_event(scheduler, time_ms, action_start_nfqueue, start_args);

    if (mark > 0) {
        action_set_mark_args *mark_args = malloc(sizeof(action_set_mark_args));
        mark_args->ctx = action;
        mark_args->queue_num = queue_num;
        mark_args->mark = mark;
        scheduler_add_event(scheduler, time_ms, action_set_mark, mark_args);
    }
    return 0;
}

// data: queue_num enable
int parse_handle_dup(scheduler_ctx *scheduler, action_ctx *action, int time_ms, char *data) {
    char *tok = data;
    int queue_num = strtol(tok, NULL, 0);
    tok = strtok(NULL, ",");
    int enable = strtol(tok, NULL, 0);

    action_set_dedup_args *dedup_args = malloc(sizeof(action_set_dedup_args));
    dedup_args->ctx = action;
    dedup_args->enable = enable;
    dedup_args->queue_num = queue_num;
    scheduler_add_event(scheduler, time_ms, action_set_dedup, dedup_args);

    return 0;
}

// data: queue_num enable rwnd
/*int parse_handle_rw(scheduler_ctx *scheduler, action_ctx *action, int time_ms, char *data) {*/
    /*char *tok = data;*/
    /*int queue_num = strtol(tok, NULL, 0);*/
    /*tok = strtok(NULL, ",");*/
    /*int enable = strtol(tok, NULL, 0);*/
    /*tok = strtok(NULL, ",");*/
    /*int rwnd = strtol(tok, NULL, 0);*/

    /*action_set_rwnd_args *rw_args = malloc(sizeof(action_set_rwnd_args));*/
    /*rw_args->ctx = action;*/
    /*rw_args->enable = enable;*/
    /*rw_args->queue_num = queue_num;*/
    /*rw_args->rwnd = rwnd;*/
    /*scheduler_add_event(scheduler, time_ms, action_set_rwnd, rw_args);*/

    /*return 0;*/
/*}*/

// data: qid enable_rw burst_sample threshold pace link prams...
int parse_init_sched(scheduler_ctx *scheduler, action_ctx *action, int time_ms, char *data) {
    char *tok = data;
    int queue_num = strtol(tok, NULL, 0);
    tok = strtok(NULL, ",");
    int enable_rw = strtol(tok, NULL, 0);
    tok = strtok(NULL, ",");
    int sample_interval = strtol(tok, NULL, 0);
    tok = strtok(NULL, ",");
    float threshold = (strtol(tok, NULL, 0) / 100.0);
    tok = strtok(NULL, ",");
    float pace = (strtol(tok, NULL, 0) / 100.0);
    tok = strtok(NULL, ",");
    int start_time = strtol(tok, NULL, 0);

    action_init_tcp_sched_args *args = malloc(sizeof(action_init_tcp_sched_args));
    args->ctx = action;
    args->enable = enable_rw;
    args->queue_num = queue_num;
    args->sample_interval = sample_interval;
    args->threshold = threshold;
    args->pace = pace;
    args->fire = start_time;
    args->mark = 1;
    // default value for lte, mmw
    for (int i=1; i<3; i++) {
        tok = strtok(NULL, ",");
        int mark = strtol(tok, NULL, 0);
        args->init_param[i].mark = mark;
        tok = strtok(NULL, ",");
        int hist_rw = strtol(tok, NULL, 0);
        args->init_param[i].hist_rw = hist_rw;
        tok = strtok(NULL, ",");
        int rtt = strtol(tok, NULL, 0);
        args->init_param[i].rtt = rtt;
    }
    scheduler_add_event(scheduler, time_ms, action_init_tcp_sched, args);
    return 0;
}

// data: queue_num enable_freeze freeze_ms enable_dedup smooth_ms burst_duration enable_adapt
// enable_adapt threshold pace
int parse_handle_solution(scheduler_ctx *scheduler, action_ctx *action, int time_ms, char *data) {
    char *tok = data;
    int queue_num = strtol(tok, NULL, 0);
    // mark
    tok = strtok(NULL, ",");
    int mark = strtol(tok, NULL, 0);
    // freeze rwnd
    tok = strtok(NULL, ",");
    int enable_freeze = strtol(tok, NULL, 0);
    tok = strtok(NULL, ",");
    int freeze_ms = strtol(tok, NULL, 0);
    // dedup
    tok = strtok(NULL, ",");
    int enable_dedup = strtol(tok, NULL, 0);
    tok = strtok(NULL, ",");
    int smooth_ms = strtol(tok, NULL, 0);
    // burst estimation
    tok = strtok(NULL, ",");
    int burst_duration = strtol(tok, NULL, 0);
    // passive adaptation
    tok = strtok(NULL, ",");
    int enable_adapt = strtol(tok, NULL, 0);

    action_sol_update_args *sol_args = malloc(sizeof(action_sol_update_args));
    sol_args->ctx = action;
    sol_args->queue_num = queue_num;
    sol_args->mark = mark;
    scheduler_add_event(scheduler, time_ms, action_sol_update, sol_args);

    // zero window until rach
    if (enable_freeze > 0) {
        // auto adjust implicitly disabled
        action_set_rwnd_args *rw_args = malloc(sizeof(action_set_rwnd_args));
        rw_args->ctx = action;
        rw_args->queue_num = queue_num;
        rw_args->rwnd = mark;
        scheduler_add_event(scheduler, time_ms, action_set_rwnd, rw_args);
    }
    time_ms += freeze_ms;
    // dedup
    if (enable_dedup > 0) {
        action_set_dedup_args *dedup_args = malloc(sizeof(action_set_dedup_args));
        dedup_args->ctx = action;
        dedup_args->enable = true;
        dedup_args->queue_num = queue_num;
        scheduler_add_event(scheduler, time_ms, action_set_dedup, dedup_args);

        action_set_dedup_args *nodedup_args = malloc(sizeof(action_set_dedup_args));
        nodedup_args->ctx = action;
        nodedup_args->enable = false;
        nodedup_args->queue_num = queue_num;
        scheduler_add_event(scheduler, time_ms + smooth_ms, action_set_dedup, dedup_args);
    }
    // burst estimation
    if (burst_duration > 0) {
        action_set_burst_args *burst_args = malloc(sizeof(action_set_burst_args));
        burst_args->ctx = action;
        burst_args->enable = true;
        burst_args->queue_num = queue_num;
        scheduler_add_event(scheduler, time_ms, action_set_burst, burst_args);

        burst_args = malloc(sizeof(action_set_burst_args));
        burst_args->ctx = action;
        burst_args->enable = false;
        burst_args->queue_num = queue_num;
        scheduler_add_event(scheduler, time_ms + burst_duration, action_set_burst, burst_args);
    }
    time_ms += burst_duration;
    // passive adaptation
    if (enable_adapt > 0) {
        action_set_adapt_args *args = malloc(sizeof(action_set_adapt_args));
        args->ctx = action;
        args->start_time = time_ms;
        args->queue_num = queue_num;
        args->enable = enable_adapt;
        scheduler_add_event(scheduler, time_ms, action_set_adapt, args);
    }
    return 0;
}

// parse events
int parse_event(scheduler_ctx *scheduler, action_ctx *action, char *text) {
    char *tmp_str, *tok;
    tmp_str = strdup(text);

    tok = strtok(tmp_str, ","); // time
    int time_ms = strtol(tok, NULL, 0);
    tok = strtok(NULL, ","); // event type
    int event = strtol(tok, NULL, 0);
    log_trace("Reading event %d", event);

    tok = strtok(NULL, ",");
    switch (event) {
        case EVENT_INIT:
            parse_init(scheduler, action, time_ms, tok);
            break;
        case EVENT_CMD:
            parse_cmd(scheduler, time_ms, tok);
            break;
        case EVENT_HO:
            parse_ho(scheduler, action, time_ms, tok);
            break;
        case EVENT_HANDLEDUP:
            parse_handle_dup(scheduler, action, time_ms, tok);
            break;
        case EVENT_HANDLERW:
            /*parse_handle_rw(scheduler, action, time_ms, tok);*/
            break;
        case EVENT_INIT_SCHED:
            parse_init_sched(scheduler, action, time_ms, tok);
            break;
        case EVENT_HANDLEDSOL:
            parse_handle_solution(scheduler, action, time_ms, tok); 
            break;
        default:
            log_error("No event matched at %d", time_ms);
            return -1;
    }
    free(tmp_str);
    return 0;
}

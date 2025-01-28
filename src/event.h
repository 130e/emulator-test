#ifndef HANDOFF_EVENT_H
#define HANDOFF_EVENT_H

#include "action.h"
#include "scheduler.h"

#define CSV_MAX_LINESZ 512

// enum {EVENT_INIT, EVENT_CMD, EVENT_HO,
//   EVENT_SOL_HANDLEDUP, EVENT_SOL_HANDLERW, EVENT_SOL_INIT_SCHED, EVENT_SOL_HO};
// Enum mapping
typedef enum {
    INIT,
    CMD,
    HO,
    SOL_HANDLEDUP,
    SOL_HANDLERW,
    SOL_INIT_SCHED,
    SOL_HO,
    UNKNOWN
} event_type;

// emulator
int parse_cmd(scheduler_ctx *scheduler, int time_ms, char *data);

// server emulator
int parse_ho(scheduler_ctx *scheduler, action_ctx *action, int time_ms, char *data);

int parse_init(scheduler_ctx *scheduler, action_ctx *action, int time_ms, char *data);

// client only
// each handover
int parse_(scheduler_ctx *scheduler, action_ctx *action, int time_ms, char *data);

int parse_handle_dup(scheduler_ctx *scheduler, action_ctx *action, int time_ms, char *data);

int parse_handle_rw(scheduler_ctx *scheduler, action_ctx *action, int time_ms, char *data);

int parse_handle_solution(scheduler_ctx *scheduler, action_ctx *action, int time_ms, char *data);

int parse_init_sched(scheduler_ctx *scheduler, action_ctx *action, int time_ms, char *data);

int parse_event(scheduler_ctx *scheduler, action_ctx *action, char *text);

#endif //HANDOFF_EVENT_H

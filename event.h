#ifndef HANDOFF_EVENT_H
#define HANDOFF_EVENT_H

#include "action.h"
#include "scheduler.h"

#define CSV_MAX_LINESZ 512

enum {EVENT_INIT, EVENT_CMD, EVENT_HO,
  EVENT_HANDLEDUP, EVENT_HANDLERW, EVENT_INIT_SCHED, EVENT_HANDLEDSOL};

// server emulator
int parse_cmd(scheduler_ctx *scheduler, int time_ms, char *data);

int parse_ho(scheduler_ctx *scheduler, action_ctx *action, int time_ms, char *data);

int parse_init(scheduler_ctx *scheduler, action_ctx *action, int time_ms, char *data);

// client only
int parse_handle_dup(scheduler_ctx *scheduler, action_ctx *action, int time_ms, char *data);

int parse_handle_rw(scheduler_ctx *scheduler, action_ctx *action, int time_ms, char *data);

int parse_handle_solution(scheduler_ctx *scheduler, action_ctx *action, int time_ms, char *data);

int parse_init_sched(scheduler_ctx *scheduler, action_ctx *action, int time_ms, char *data);

int parse_init_sched(scheduler_ctx *scheduler, action_ctx *action, int time_ms, char *data);

int parse_event(scheduler_ctx *scheduler, action_ctx *action, char *text);

#endif //HANDOFF_EVENT_H

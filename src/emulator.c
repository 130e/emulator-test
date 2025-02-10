#include <stdio.h>
#include <unistd.h>
#include <arpa/inet.h>

#include "action.h"
#include "nfqueue.h"
#include "worker.h"
#include "scheduler.h"
#include "log.h"
#include "event.h"

pthread_mutex_t log_lock = PTHREAD_MUTEX_INITIALIZER;

void do_log_lock(bool lock, void *udata)
{
  if (lock)
    pthread_mutex_lock(&log_lock);
  else
    pthread_mutex_unlock(&log_lock);
}

// 0 output queue, 1 input queue
// action is queues and workers, one
// scheduler is one clock
// each event might needs diff args
int main(int argc, char **argv)
{
  if (argc < 3)
  {
    log_fatal("./emulator {run id} {input csv}");
    return -1;
  }

  char *id = argv[1];
  printf("[Emulator] %s\n", id);

  log_set_lock(do_log_lock, NULL);
  // Logging setting
  log_set_level(LOG_FATAL);
  log_set_quiet(true);
  FILE *logFile = fopen("./packet.log", "w");
  if (logFile == NULL)
    return -1;
  log_add_fp(logFile, LOG_FATAL);

  // main scheduler
  scheduler_ctx scheduler;
  scheduler_init_ctx(&scheduler, id);

  // main action ctx
  action_ctx action;
  action_init_ctx(&action);

  // sched init. tcp_sched is in action_ctx
  // and called by scheduler_run to wake up and tune tcp
  tcp_ctx tcp_scheduler;
  init_tcp_scheduler(&tcp_scheduler, &action);

  // read input
  printf("Reading input\n");
  FILE *stream = fopen(argv[2], "r");
  if (stream == NULL)
  {
    printf("Error reading file %s\n", argv[2]);
    return -1;
  }
  char line[CSV_MAX_LINESZ];
  while (fgets(line, CSV_MAX_LINESZ, stream) != NULL)
  {
    parse_event(&scheduler, &action, line);
  }

  // Debugging
  // manual script event
  /*int end_ms = 30000;*/
  /*int simu_end_ms = end_ms + 3000;*/
  /*// output queue*/
  /*action_init_nfqueue_args action_init_args = {.ctx = &action, .queue_num = 0};*/
  /*scheduler_add_event(&scheduler, 0, action_init_nfqueue, &action_init_args);*/
  /*action_teardown_nfqueue_args action_teardown_args = {.ctx = &action, .queue_num = 0};*/
  /*scheduler_add_event(&scheduler, simu_end_ms, action_teardown_nfqueue, &action_teardown_args);*/
  /*action_start_nfqueue_args action_start_args = {.ctx = &action, .queue_num = 0};*/
  /*scheduler_add_event(&scheduler, 0, action_start_nfqueue, &action_start_args);*/

  /*// input*/
  /*action_init_nfqueue_args action_init1_args = {.ctx = &action, .queue_num = 1};*/
  /*scheduler_add_event(&scheduler, 0, action_init_nfqueue, &action_init1_args);*/
  /*action_teardown_nfqueue_args action_teardown1_args = {.ctx = &action, .queue_num = 1};*/
  /*scheduler_add_event(&scheduler, simu_end_ms, action_teardown_nfqueue, &action_teardown1_args);*/
  /*action_start_nfqueue_args action_start1_args = {.ctx = &action, .queue_num = 1};*/
  /*scheduler_add_event(&scheduler, 0, action_start_nfqueue, &action_start1_args);*/

  /*// mark*/
  /*action_set_mark_args action_mark_args = {.ctx = &action, .queue_num = 0, .mark = 1};*/
  /*scheduler_add_event(&scheduler, 0, action_set_mark, &action_mark_args);*/

  printf("Emulator starts\n");
  // start scheduler
  scheduler_run(&scheduler, &tcp_scheduler);

  // clean up
  printf("Emulator ends\n");
  scheduler_destroy_ctx(&scheduler);
  action_destroy_ctx(&action);

  return 0;
}

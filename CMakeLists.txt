cmake_minimum_required(VERSION 3.0)
project(handoff C)

set(CMAKE_C_STANDARD 99)

add_definitions(-DLOG_USE_COLOR)
add_executable(handoff main.c nfqueue.c nfqueue.h log.c log.h worker.c worker.h scheduler.c scheduler.h action.c action.h event.c)

TARGET_LINK_LIBRARIES(handoff pthread netfilter_queue nfnetlink)

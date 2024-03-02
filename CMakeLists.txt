# WIP not working
cmake_minimum_required(VERSION 3.10)
project(m2ho C)

set(CMAKE_EXE_LINKER_FLAGS "-static")

# add_executable(handoff main.c nfqueue.c nfqueue.h log.c log.h worker.c worker.h scheduler.c scheduler.h action.c action.h event.c)

add_executable(client main.c)
target_link_directories(client PUBLIC {CMAKE_SOURCE_DIR}/lib/lib)
target_link_libraries(client pthread netfilter_queue nfnetlink)

# add_executable(server server.c)
# target_link_libraries(handoff pthread netfilter_queue nfnetlink)

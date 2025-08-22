cmake_minimum_required(VERSION 3.10)
project(M2HO)

set(CMAKE_EXE_LINKER_FLAGS "-static")

# Set paths for local libraries
set(LIB_DIR ${CMAKE_SOURCE_DIR}/lib)
include_directories(${LIB_DIR}/include)
link_directories(${LIB_DIR}/lib)

# Define source files
file(GLOB SOURCES ${CMAKE_SOURCE_DIR}/src/*.c *.h)
#set(SOURCES emulator.c nfqueue.c nfqueue.h log.c log.h worker.c worker.h scheduler.c scheduler.h action.c action.h event.c)

# Add executable target
add_executable(emulator ${SOURCES})
#target_link_libraries(emulator pthread netfilter_queue nfnetlink)
target_link_libraries(emulator pthread ${LIB_DIR}/lib/libnetfilter_queue.a ${LIB_DIR}/lib/libnfnetlink.a)

#target_link_directories(client PUBLIC ${CMAKE_SOURCE_DIR}/lib/lib)
#target_link_libraries(client pthread netfilter_queue nfnetlink)
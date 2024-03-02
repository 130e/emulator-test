# temporary debug makefile. Should use cmake eventually
CC=gcc
# CFLAGS=-O -lnetfilter_queue -L/home/sunfish/Projects/emulator-test/lib/lib -lnfnetlink -static
CFLAGS=-O -lpthread -lnetfilter_queue -L/home/sunfish/Projects/emulator-test/lib/lib -lnfnetlink

CLDEPS=nfqueue.c nfqueue.h log.c log.h worker.c worker.h scheduler.c scheduler.h action.c action.h event.c

client:
	$(CC) -o client main.c $(CLDEPS) $(CFLAGS)

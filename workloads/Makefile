# build static risc-v binaries into workloads/bin/.
#   make -C workloads CC=<riscv64 linux gcc>
# todo(jacob): confirm the cross-compiler and flags.
CC ?= riscv64-linux-gnu-gcc
CFLAGS ?= -O2 -static

PROGS := predictable unpredictable phased
BINS := $(addprefix bin/,$(PROGS))

all: $(BINS)

.SECONDEXPANSION:
bin/%: src/$$*/$$*.c | bin
	$(CC) $(CFLAGS) -o $@ $<

bin:
	mkdir -p bin

clean:
	rm -rf bin

.PHONY: all clean

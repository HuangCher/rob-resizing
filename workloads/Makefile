# Build static RISC-V Linux executables for gem5 syscall-emulation (SE) mode.
# From the project root: make -C workloads
# Override if needed:  make -C workloads CC=/path/to/riscv64-linux-gnu-gcc
#                      make -C workloads CC=gcc   # native smoke test only

# GNU Make already defines CC=cc, so a simple 'CC ?=' would leave CC=cc.
# Use the cross-compiler only when CC has not been explicitly provided.
ifeq ($(origin CC),default)
CC := riscv64-linux-gnu-gcc
endif

CFLAGS ?= -std=c11 -O2 -static -fno-if-conversion -fno-if-conversion2 -fno-tree-vectorize -fno-unroll-loops -fno-lto -Wall -Wextra -Werror

PROGS := predictable unpredictable phased
BINS := $(addprefix bin/,$(PROGS))

all: $(BINS)

.SECONDEXPANSION:
# Rebuild when the common benchmark header changes, not just the C source.
bin/%: src/$$*/$$*.c src/common/benchmark.h | bin
	$(CC) $(CFLAGS) $(CPPFLAGS) -o $@ $< $(LDFLAGS)

bin:
	mkdir -p bin

clean:
	rm -rf bin

.PHONY: all clean

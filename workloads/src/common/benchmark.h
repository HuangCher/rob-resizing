#ifndef ROB_BENCHMARK_H
#define ROB_BENCHMARK_H

#include <errno.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

/* A fixed 16 KiB data footprint, sized to fit a typical L1-D cache. */
#define PATTERN_SIZE (1u << 14)
#define PATTERN_MASK (PATTERN_SIZE - 1u)
#define DEFAULT_TOTAL_ITERATIONS UINT64_C(180000)
#define DEFAULT_PHASES UINT64_C(6)
#define DEFAULT_PHASE_ITERATIONS (DEFAULT_TOTAL_ITERATIONS / DEFAULT_PHASES)

#if defined(__GNUC__)
#define BENCH_NOINLINE __attribute__((noinline, noclone))
#else
#define BENCH_NOINLINE
#endif

/* Data is generated deterministically: identical values on every run. */
static void
init_pattern(uint8_t pattern[PATTERN_SIZE])
{
    uint32_t state = UINT32_C(0x9e3779b9);
    for (size_t i = 0; i < PATTERN_SIZE; ++i) {
        state = state * UINT32_C(1664525) + UINT32_C(1013904223);
        pattern[i] = (uint8_t)((state >> 13) ^ (state >> 21));
    }
}

static int
parse_positive_u64(const char *str, uint64_t *out)
{
    char *end = NULL;
    unsigned long long value;
    if (!str || !*str || *str == '-')
        return -1;
    errno = 0;
    value = strtoull(str, &end, 10);
    if (errno != 0 || end == str || *end != '\0' || value == 0)
        return -1;
    *out = (uint64_t)value;
    return 0;
}

/* The workload branches use identical payload code in all three programs.
 * Different branch outcome streams, not different arithmetic, are the test.
 */
#define BENCH_PAYLOAD(take, input, index, sum_t, sum_nt, xor_t, xor_nt) \
    do {                                                               \
        const uint64_t v = (uint64_t)(input) + ((index) & 31u);         \
        if (take) {                                                    \
            (sum_t) += v;                                              \
            (xor_t) = ((xor_t) << 1) ^ (v + (index));                    \
        } else {                                                       \
            (sum_nt) += v;                                             \
            (xor_nt) = ((xor_nt) << 1) ^ (v + (index));                  \
        }                                                              \
    } while (0)

#define BENCH_CHECKSUM(sum_t, sum_nt, xor_t, xor_nt) \
    ((sum_t) ^ ((sum_nt) << 1) ^ ((xor_t) << 2) ^ ((xor_nt) << 3))

#endif /* ROB_BENCHMARK_H */

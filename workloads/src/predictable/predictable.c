/* Predictable branch workload. 255 of every 256 conditional outcomes are
 * taken; the unconditional data work matches the unpredictable benchmark.
 * Build with -fno-if-conversion -fno-if-conversion2, then inspect disassembly.
 */
#include "../common/benchmark.h"

static uint8_t pattern[PATTERN_SIZE];

static uint64_t BENCH_NOINLINE
run_kernel(uint64_t iterations)
{
    uint64_t sum_t = 0, sum_nt = 0, xor_t = 0, xor_nt = 0;
    for (uint64_t i = 0; i < iterations; ++i) {
        uint8_t input = pattern[i & PATTERN_MASK];
        int take = (i & UINT64_C(255)) != 0;
        BENCH_PAYLOAD(take, input, i, sum_t, sum_nt, xor_t, xor_nt);
    }
    return BENCH_CHECKSUM(sum_t, sum_nt, xor_t, xor_nt);
}

int
main(int argc, char **argv)
{
    uint64_t iterations = DEFAULT_TOTAL_ITERATIONS;
    if (argc > 2 || (argc == 2 && parse_positive_u64(argv[1], &iterations))) {
        fprintf(stderr, "usage: %s [positive_iterations]\n", argv[0]);
        return 2;
    }
    init_pattern(pattern);
    printf("kind=predictable iterations=%" PRIu64 " checksum=%016" PRIx64 "\n",
           iterations, run_kernel(iterations));
    return 0;
}

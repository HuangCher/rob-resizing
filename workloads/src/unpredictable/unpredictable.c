/* Unpredictable branch workload. The condition is a ~50/50 pseudorandom
 * data-dependent bit read from a fixed, reproducible 16 KiB array.
 * Inspect the RISC-V run_kernel disassembly for a genuine conditional branch.
 */
#include "../common/benchmark.h"

static uint8_t pattern[PATTERN_SIZE];

static uint64_t BENCH_NOINLINE
run_kernel(uint64_t iterations)
{
    uint64_t sum_t = 0, sum_nt = 0, xor_t = 0, xor_nt = 0;
    for (uint64_t i = 0; i < iterations; ++i) {
        uint8_t input = pattern[i & PATTERN_MASK];
        int take = (input & 1u) != 0;
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
    printf("kind=unpredictable iterations=%" PRIu64 " checksum=%016" PRIx64 "\n",
           iterations, run_kernel(iterations));
    return 0;
}

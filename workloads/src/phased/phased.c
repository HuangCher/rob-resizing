/* Phased workload: alternating predictable and unpredictable branch outcome
 * streams at the SAME static payload branch site, to exercise ROB resizing.
 * Phase 0 is predictable; odd phases are unpredictable. Both use the same
 * deterministic data array and arithmetic as the single-mode workloads.
 */
#include "../common/benchmark.h"

static uint8_t pattern[PATTERN_SIZE];

static uint64_t BENCH_NOINLINE
run_kernel(uint64_t iterations_per_phase, uint64_t phases)
{
    uint64_t sum_t = 0, sum_nt = 0, xor_t = 0, xor_nt = 0;
    for (uint64_t phase = 0; phase < phases; ++phase) {
        int unpredictable = (phase & UINT64_C(1)) != 0;
        for (uint64_t j = 0; j < iterations_per_phase; ++j) {
            uint64_t i = phase * iterations_per_phase + j;
            uint8_t input = pattern[i & PATTERN_MASK];
            int take = unpredictable ? ((input & 1u) != 0)
                                     : ((j & UINT64_C(255)) != 0);
            BENCH_PAYLOAD(take, input, i, sum_t, sum_nt, xor_t, xor_nt);
        }
    }
    return BENCH_CHECKSUM(sum_t, sum_nt, xor_t, xor_nt);
}

int
main(int argc, char **argv)
{
    uint64_t iterations_per_phase = DEFAULT_PHASE_ITERATIONS;
    uint64_t phases = DEFAULT_PHASES;
    if (argc > 3 ||
        (argc >= 2 && parse_positive_u64(argv[1], &iterations_per_phase)) ||
        (argc == 3 && parse_positive_u64(argv[2], &phases)) ||
        phases > UINT64_MAX / iterations_per_phase) {
        fprintf(stderr, "usage: %s [positive_iterations_per_phase] [positive_phases]\n",
                argv[0]);
        return 2;
    }
    init_pattern(pattern);
    printf("kind=phased phases=%" PRIu64 " iterations_per_phase=%" PRIu64
           " total_iterations=%" PRIu64 " checksum=%016" PRIx64 "\n",
           phases, iterations_per_phase, phases * iterations_per_phase,
           run_kernel(iterations_per_phase, phases));
    return 0;
}

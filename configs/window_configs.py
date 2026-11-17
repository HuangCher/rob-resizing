"""rob / iq / lsq sizes and branch predictor choices for the sweep.

plain python with no gem5 imports, so both the gem5 config script and the
host-side experiment runner can import it.
"""

# rob entries per config. "dynamic" uses the large size as its physical
# rob and lets the resizer cap it at runtime.
ROB_ENTRIES = {
    "small": 64,
    "medium": 128,
    "large": 256,
    "massive": 512,
    "dynamic": 256,
}

# rob entries the dynamic config drops to when prediction is poor
DYNAMIC_RESTRICTED_ROB = 64

# iq / lq / sq as a fraction of rob size.
# placeholder: not decided yet. rob/4 and rob/8 make the large config use
# gem5's stock iq (64) and lq/sq (32) sizes.
IQ_RATIO = 1 / 4
LQ_RATIO = 1 / 8
SQ_RATIO = 1 / 8

# predictor key -> label used in result paths
PREDICTORS = {
    "tage": "high accuracy (tage)",
    "local": "low accuracy (2-bit local)",
}


def window_sizes(config: str) -> dict:
    """return the physical rob/iq/lq/sq sizes for a config name."""
    if config not in ROB_ENTRIES:
        raise ValueError(
            f"unknown rob config '{config}', expected one of "
            f"{sorted(ROB_ENTRIES)}"
        )
    rob = ROB_ENTRIES[config]
    return {
        "rob": rob,
        "iq": max(1, round(rob * IQ_RATIO)),
        "lq": max(1, round(rob * LQ_RATIO)),
        "sq": max(1, round(rob * SQ_RATIO)),
    }

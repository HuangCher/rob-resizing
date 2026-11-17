"""rob / iq / lsq / register sizes for each config in the sweep.

owner: newman. plain python with no gem5 imports, so both the gem5 config
and the experiment runner can import it.
"""

# rob entries per config (from the project spec). "dynamic" uses the large
# size as its physical rob and lets the resizer cap it at runtime.
ROB_ENTRIES = {
    "small": 64,
    "medium": 128,
    "large": 256,
    "massive": 512,
    "dynamic": 256,
}

# rob entries the dynamic config drops to when prediction is poor
DYNAMIC_RESTRICTED_ROB = 64


def window_sizes(config: str) -> dict:
    """return the physical rob/iq/lq/sq/register sizes for a config."""
    raise NotImplementedError("todo(newman)")

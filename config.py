import os
# =============================================================================
# 📐 CONFIGURABLE CONSTANTS
# =============================================================================
COST_ESTIMATE_RATIO = 0.85
BID_RATIO_DECIMALS = 4
BID_AMOUNT_DECIMALS = 3

# =============================================================================
# 📐 CONFIGURABLE PPR CONSTANTS
# =============================================================================
#PPR_CONFIG = {
#    'nppi_factor': 0.920,
#    'weights': {'competitor_avg': 0.5, 'official_est': 0.2, 'nppi': 0.3},
#    'slt_buffer': 1.0
#}



# =============================================================================
# 📐 CONFIGURABLE PPR CONSTANTS
# =============================================================================
PPR_CONFIG = {
    'nppi_factor': float(os.getenv('PPR_NPPI_FACTOR', '0.920')),  # ✅ Configurable
    'weights': {'competitor_avg': 0.5, 'official_est': 0.2, 'nppi': 0.3},
    'slt_buffer': 1.0  # Standard deviation multiplier
}


DEBUG_MODE = True

def debug_print(*args, **kwargs):
    if DEBUG_MODE:
        print(*args, **kwargs)

"""
DRS Zone configurations for F1 2024 tracks.

All configurations validated against FastF1 2024 data.
"""

from drs.zones.monaco_2024 import get_config as get_monaco_config, monaco_2024_config
from drs.zones.monza_2024 import get_config as get_monza_config, monza_2024_config
from drs.zones.spain_2024 import get_config as get_spain_config
from drs.zones.bahrain_2024 import get_config as get_bahrain_config
from drs.zones.australia_2024 import get_config as get_australia_config
from drs.zones.japan_2024 import get_config as get_japan_config
from drs.zones.china_2024 import get_config as get_china_config
from drs.zones.italy_2024 import get_config as get_italy_config

# All available track configurations
TRACKS = {
    "Monaco": get_monaco_config,
    "Monza": get_monza_config,
    "Spain": get_spain_config,
    "Bahrain": get_bahrain_config,
    "Australia": get_australia_config,
    "Japan": get_japan_config,
    "China": get_china_config,
    "Italy": get_italy_config,
}

__all__ = [
    "get_monaco_config",
    "get_monza_config",
    "get_spain_config",
    "get_bahrain_config",
    "get_australia_config",
    "get_japan_config",
    "get_china_config",
    "get_italy_config",
    "TRACKS",
]

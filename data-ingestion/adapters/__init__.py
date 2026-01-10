# Data adapters module
"""
Data source adapters for Viral Weather platform.

Each adapter handles fetching and normalizing data from a specific source:
- Wastewater surveillance (CDC, UKHSA, RIVM, RKI, etc.)
- Flight data (AviationStack)
- Genomic data (Nextstrain - future)
"""

from .base import (
    BaseAdapter,
    LocationData,
    SurveillanceEvent,
    SignalType,
    GranularityTier,
)

# Wastewater adapters
from .cdc_nwss import CDCNWSSAdapter
from .uk_ukhsa import UKUKHSAAdapter
from .nl_rivm import NLRIVMAdapter
from .de_rki import DERKIAdapter
from .fr_datagouv import FRDataGouvAdapter
from .jp_niid import JPNIIDAdapter
from .au_health import AUHealthAdapter

# Flight data adapter
from .aviationstack import (
    AviationStackAdapter,
    FlightRoute,
    VectorArc,
    calculate_import_pressure,
)

# Registry of all wastewater adapters
WASTEWATER_ADAPTERS = {
    "CDC_NWSS": CDCNWSSAdapter,
    "UKHSA": UKUKHSAAdapter,
    "RIVM": NLRIVMAdapter,
    "RKI": DERKIAdapter,
    "FR_DATAGOUV": FRDataGouvAdapter,
    "NIID": JPNIIDAdapter,
    "AU_HEALTH": AUHealthAdapter,
}


async def run_all_wastewater_adapters():
    """
    Run all wastewater adapters and collect results.

    Returns:
        Tuple of (all_locations, all_events)
    """
    all_locations = []
    all_events = []

    for name, adapter_class in WASTEWATER_ADAPTERS.items():
        try:
            adapter = adapter_class()
            raw_data = await adapter.fetch()
            locations, events = adapter.normalize(raw_data)
            all_locations.extend(locations)
            all_events.extend(events)
            await adapter.close()
            print(f"[{name}] Fetched {len(locations)} locations, {len(events)} events")
        except Exception as e:
            print(f"[{name}] Error: {e}")
            continue

    return all_locations, all_events


__all__ = [
    # Base classes
    "BaseAdapter",
    "LocationData",
    "SurveillanceEvent",
    "SignalType",
    "GranularityTier",
    # Wastewater adapters
    "CDCNWSSAdapter",
    "UKUKHSAAdapter",
    "NLRIVMAdapter",
    "DERKIAdapter",
    "FRDataGouvAdapter",
    "JPNIIDAdapter",
    "AUHealthAdapter",
    # Flight adapter
    "AviationStackAdapter",
    "FlightRoute",
    "VectorArc",
    "calculate_import_pressure",
    # Utilities
    "WASTEWATER_ADAPTERS",
    "run_all_wastewater_adapters",
]

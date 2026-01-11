# Data adapters module
"""
Data source adapters for Viral Weather platform.

Each adapter handles fetching and normalizing data from a specific source:
- Wastewater surveillance (CDC, UKHSA, RIVM, RKI, EU Observatory, etc.)
- Flight data (AviationStack)
- Genomic data (Nextstrain)
"""

from .base import (
    BaseAdapter,
    LocationData,
    SurveillanceEvent,
    SignalType,
    GranularityTier,
)

# Wastewater adapters - Original
from .cdc_nwss import CDCNWSSAdapter
from .uk_ukhsa import UKUKHSAAdapter
from .nl_rivm import NLRIVMAdapter
from .de_rki import DERKIAdapter
from .fr_datagouv import FRDataGouvAdapter
from .jp_niid import JPNIIDAdapter
from .au_health import AUHealthAdapter

# Wastewater adapters - EU and International (new)
from .eu_wastewater import (
    EUWastewaterObservatoryAdapter,
    SpainISCIIIAdapter,
    CanadaWastewaterAdapter,
    NewZealandESRAdapter,
)

# Wastewater adapters - APAC (new)
from .apac_wastewater import (
    SingaporeNEAAdapter,
    SouthKoreaKDCAAdapter,
)

# Wastewater adapters - South America (new)
from .brazil_wastewater import BrazilFiocruzAdapter

# Genomic data adapter (new)
from .nextstrain import NextstrainAdapter

# Flight data adapter
from .aviationstack import (
    AviationStackAdapter,
    FlightRoute,
    VectorArc,
    calculate_import_pressure,
)

# Registry of all wastewater adapters
WASTEWATER_ADAPTERS = {
    # Original adapters
    "CDC_NWSS": CDCNWSSAdapter,
    "UKHSA": UKUKHSAAdapter,
    "RIVM": NLRIVMAdapter,
    "RKI": DERKIAdapter,
    "FR_DATAGOUV": FRDataGouvAdapter,
    "NIID": JPNIIDAdapter,
    "AU_HEALTH": AUHealthAdapter,
    # EU/International adapters
    "EU_OBSERVATORY": EUWastewaterObservatoryAdapter,
    "ES_ISCIII": SpainISCIIIAdapter,
    "CA_PHAC": CanadaWastewaterAdapter,
    "NZ_ESR": NewZealandESRAdapter,
    # APAC adapters
    "SG_NEA": SingaporeNEAAdapter,
    "KR_KDCA": SouthKoreaKDCAAdapter,
    # South America adapters
    "BR_FIOCRUZ": BrazilFiocruzAdapter,
}

# Registry of genomic adapters
GENOMIC_ADAPTERS = {
    "NEXTSTRAIN": NextstrainAdapter,
}

# Registry of flight data adapters
FLIGHT_ADAPTERS = {
    "AVIATIONSTACK": AviationStackAdapter,
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


async def run_all_genomic_adapters():
    """
    Run all genomic data adapters and collect results.

    Returns:
        Tuple of (all_locations, all_events)
    """
    all_locations = []
    all_events = []

    for name, adapter_class in GENOMIC_ADAPTERS.items():
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


async def run_all_adapters():
    """
    Run all adapters (wastewater, genomic, flight) and collect results.

    Returns:
        Dict with all_locations, all_events, and adapter_status
    """
    all_locations = []
    all_events = []
    adapter_status = {}

    # Run wastewater adapters
    for name, adapter_class in WASTEWATER_ADAPTERS.items():
        try:
            adapter = adapter_class()
            raw_data = await adapter.fetch()
            locations, events = adapter.normalize(raw_data)
            all_locations.extend(locations)
            all_events.extend(events)
            await adapter.close()
            adapter_status[name] = {
                "success": True,
                "locations": len(locations),
                "events": len(events),
            }
            print(f"[{name}] Fetched {len(locations)} locations, {len(events)} events")
        except Exception as e:
            adapter_status[name] = {"success": False, "error": str(e)}
            print(f"[{name}] Error: {e}")
            continue

    # Run genomic adapters
    for name, adapter_class in GENOMIC_ADAPTERS.items():
        try:
            adapter = adapter_class()
            raw_data = await adapter.fetch()
            locations, events = adapter.normalize(raw_data)
            all_locations.extend(locations)
            all_events.extend(events)
            await adapter.close()
            adapter_status[name] = {
                "success": True,
                "locations": len(locations),
                "events": len(events),
            }
            print(f"[{name}] Fetched {len(locations)} locations, {len(events)} events")
        except Exception as e:
            adapter_status[name] = {"success": False, "error": str(e)}
            print(f"[{name}] Error: {e}")
            continue

    return {
        "locations": all_locations,
        "events": all_events,
        "adapter_status": adapter_status,
    }


__all__ = [
    # Base classes
    "BaseAdapter",
    "LocationData",
    "SurveillanceEvent",
    "SignalType",
    "GranularityTier",
    # Wastewater adapters - Original
    "CDCNWSSAdapter",
    "UKUKHSAAdapter",
    "NLRIVMAdapter",
    "DERKIAdapter",
    "FRDataGouvAdapter",
    "JPNIIDAdapter",
    "AUHealthAdapter",
    # Wastewater adapters - EU/International
    "EUWastewaterObservatoryAdapter",
    "SpainISCIIIAdapter",
    "CanadaWastewaterAdapter",
    "NewZealandESRAdapter",
    # Wastewater adapters - APAC
    "SingaporeNEAAdapter",
    "SouthKoreaKDCAAdapter",
    # Wastewater adapters - South America
    "BrazilFiocruzAdapter",
    # Genomic adapters
    "NextstrainAdapter",
    # Flight adapter
    "AviationStackAdapter",
    "FlightRoute",
    "VectorArc",
    "calculate_import_pressure",
    # Registries
    "WASTEWATER_ADAPTERS",
    "GENOMIC_ADAPTERS",
    "FLIGHT_ADAPTERS",
    # Utilities
    "run_all_wastewater_adapters",
    "run_all_genomic_adapters",
    "run_all_adapters",
]

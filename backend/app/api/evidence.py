"""
Evidence chain API for showing causal links between traveler detection and local emergence.
"""

from datetime import datetime, date, timedelta
from typing import Optional, List
import random
import hashlib

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/evidence", tags=["evidence"])


class EvidenceEvent(BaseModel):
    """Single event in the evidence chain."""
    event_id: str
    event_type: str  # 'traveler_detection', 'genomic_detection', 'wastewater_spike'
    date: str
    variant_id: str
    description: str
    source_location: Optional[str] = None
    count: Optional[int] = None
    confidence: float
    icon: str


class EvidenceChainResponse(BaseModel):
    """Complete evidence chain for a location/variant pair."""
    location_id: str
    location_name: str
    variant_id: str
    events: List[EvidenceEvent]
    lead_time_days: Optional[int] = None
    chain_confidence: float
    summary: str


# Event type configurations
EVENT_TYPES = {
    'traveler_detection': {
        'icon': '✈️',
        'template': '{count} travelers from {source} tested positive for {variant}',
    },
    'genomic_detection': {
        'icon': '🧬',
        'template': '{variant} detected in wastewater genomic sequencing ({percentage}% of samples)',
    },
    'wastewater_spike': {
        'icon': '📈',
        'template': 'Wastewater viral concentration increased {change}% week-over-week',
    },
    'clinical_cases': {
        'icon': '🏥',
        'template': 'First clinical cases of {variant} confirmed',
    },
}

# Sample origin cities for traveler data
ORIGIN_CITIES = [
    "Tokyo", "London", "Paris", "Dubai", "Singapore",
    "Sydney", "Frankfurt", "Amsterdam", "Seoul", "Hong Kong",
]


def generate_evidence_chain(
    location_id: str,
    location_name: str,
    variant_id: str,
    days: int = 60,
) -> EvidenceChainResponse:
    """Generate synthetic evidence chain for demonstration."""
    seed = int(hashlib.md5(f"{location_id}_{variant_id}".encode()).hexdigest()[:8], 16)
    random.seed(seed)

    events = []
    today = date.today()

    # Generate traveler detection event (earliest)
    traveler_days_ago = random.randint(30, min(days - 10, 50))
    traveler_date = today - timedelta(days=traveler_days_ago)
    origin_city = random.choice(ORIGIN_CITIES)
    traveler_count = random.randint(1, 5)

    events.append(EvidenceEvent(
        event_id=f"ev_{location_id}_{variant_id}_traveler",
        event_type="traveler_detection",
        date=traveler_date.isoformat(),
        variant_id=variant_id,
        description=f"{traveler_count} travelers from {origin_city} tested positive for {variant_id}",
        source_location=origin_city,
        count=traveler_count,
        confidence=random.uniform(0.85, 0.98),
        icon="✈️",
    ))

    # Generate genomic detection event (5-14 days later)
    genomic_delay = random.randint(5, 14)
    genomic_date = traveler_date + timedelta(days=genomic_delay)
    genomic_percentage = random.uniform(0.1, 2.5)

    events.append(EvidenceEvent(
        event_id=f"ev_{location_id}_{variant_id}_genomic",
        event_type="genomic_detection",
        date=genomic_date.isoformat(),
        variant_id=variant_id,
        description=f"{variant_id} detected in local wastewater genomic sequencing ({genomic_percentage:.1f}% of samples)",
        confidence=random.uniform(0.75, 0.95),
        icon="🧬",
    ))

    # Generate wastewater spike event (7-21 days after traveler detection)
    spike_delay = random.randint(7, 21)
    spike_date = traveler_date + timedelta(days=spike_delay)
    spike_change = random.randint(15, 150)

    events.append(EvidenceEvent(
        event_id=f"ev_{location_id}_{variant_id}_spike",
        event_type="wastewater_spike",
        date=spike_date.isoformat(),
        variant_id=variant_id,
        description=f"Wastewater viral concentration increased {spike_change}% week-over-week",
        confidence=random.uniform(0.80, 0.95),
        icon="📈",
    ))

    # Optionally add clinical cases (not always present)
    if random.random() > 0.3:
        clinical_delay = random.randint(14, 28)
        clinical_date = traveler_date + timedelta(days=clinical_delay)

        events.append(EvidenceEvent(
            event_id=f"ev_{location_id}_{variant_id}_clinical",
            event_type="clinical_cases",
            date=clinical_date.isoformat(),
            variant_id=variant_id,
            description=f"First clinical cases of {variant_id} confirmed in local population",
            confidence=random.uniform(0.90, 0.99),
            icon="🏥",
        ))

    # Sort by date
    events.sort(key=lambda e: e.date)

    # Calculate lead time (traveler detection to wastewater spike)
    lead_time = (spike_date - traveler_date).days

    # Calculate overall chain confidence
    chain_confidence = min([e.confidence for e in events]) * 0.9

    # Generate summary
    summary = (
        f"{variant_id} was first detected in {traveler_count} traveler(s) from {origin_city} "
        f"on {traveler_date.strftime('%b %d')}, providing {lead_time} days of early warning "
        f"before the wastewater spike on {spike_date.strftime('%b %d')}."
    )

    random.seed()  # Reset seed
    return EvidenceChainResponse(
        location_id=location_id,
        location_name=location_name,
        variant_id=variant_id,
        events=events,
        lead_time_days=lead_time,
        chain_confidence=round(chain_confidence, 2),
        summary=summary,
    )


# Location name mapping (subset for demo)
LOCATION_NAMES = {
    "loc_us_new_york": "New York",
    "loc_us_los_angeles": "Los Angeles",
    "loc_us_chicago": "Chicago",
    "loc_gb_london": "London",
    "loc_de_berlin": "Berlin",
    "loc_fr_paris": "Paris",
    "loc_jp_tokyo": "Tokyo",
    "loc_au_sydney": "Sydney",
    "loc_sg_singapore": "Singapore",
    "loc_ae_dubai": "Dubai",
}

VARIANTS = ["BA.2.86", "JN.1", "JN.1.1", "XBB.1.5", "EG.5"]


@router.get("/chain/{location_id}/{variant_id}", response_model=EvidenceChainResponse)
async def get_evidence_chain(
    location_id: str,
    variant_id: str,
    days: int = Query(60, ge=30, le=180, description="Days of history to analyze"),
):
    """
    Get evidence chain showing how a variant was detected at a location.

    Builds a chronological chain of events from:
    1. First traveler detection
    2. Genomic detection in wastewater
    3. Wastewater concentration spike
    4. (Optional) First clinical cases

    Returns the chain with lead time calculation showing early warning value.
    """
    if variant_id not in VARIANTS:
        raise HTTPException(status_code=404, detail=f"Unknown variant: {variant_id}")

    location_name = LOCATION_NAMES.get(location_id, location_id.replace("loc_", "").replace("_", " ").title())

    chain = generate_evidence_chain(location_id, location_name, variant_id, days)
    return chain


@router.get("/chains/{location_id}")
async def get_all_evidence_chains(
    location_id: str,
    days: int = Query(60, ge=30, le=180, description="Days of history"),
):
    """
    Get evidence chains for all variants detected at a location.
    """
    location_name = LOCATION_NAMES.get(location_id, location_id.replace("loc_", "").replace("_", " ").title())

    # Generate chains for a subset of variants
    seed = int(hashlib.md5(location_id.encode()).hexdigest()[:8], 16)
    random.seed(seed)

    # Select 2-4 variants for this location
    num_variants = random.randint(2, min(4, len(VARIANTS)))
    location_variants = random.sample(VARIANTS, num_variants)

    random.seed()

    chains = []
    for variant_id in location_variants:
        chain = generate_evidence_chain(location_id, location_name, variant_id, days)
        chains.append(chain)

    # Sort by lead time (most valuable first)
    chains.sort(key=lambda c: c.lead_time_days or 0, reverse=True)

    return {
        "location_id": location_id,
        "location_name": location_name,
        "chains": chains,
        "total_chains": len(chains),
    }

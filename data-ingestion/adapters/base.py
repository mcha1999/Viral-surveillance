"""
Base adapter class for all data sources
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum

import structlog

logger = structlog.get_logger()


class SignalType(str, Enum):
    """Types of surveillance signals."""
    WASTEWATER = "wastewater"
    GENOMIC = "genomic"
    FLIGHT = "flight"


class GranularityTier(str, Enum):
    """Data granularity tiers."""
    TIER_1 = "tier_1"  # Point-exact (site level)
    TIER_2 = "tier_2"  # Admin-1 (state/province)
    TIER_3 = "tier_3"  # Country level


@dataclass
class LocationData:
    """Normalized location data."""
    location_id: str
    name: str
    admin1: Optional[str]
    country: str
    iso_code: str
    granularity: GranularityTier
    latitude: float
    longitude: float
    catchment_population: Optional[int] = None
    h3_index: Optional[str] = None


@dataclass
class SurveillanceEvent:
    """Normalized surveillance event."""
    event_id: str
    location_id: str
    timestamp: datetime
    data_source: str
    signal_type: SignalType

    # Wastewater metrics
    raw_load: Optional[float] = None
    normalized_score: Optional[float] = None  # 0-1 scale
    velocity: Optional[float] = None  # Week-over-week change

    # Genomic data
    confirmed_variants: List[str] = field(default_factory=list)
    suspected_variants: List[str] = field(default_factory=list)

    # Quality
    quality_score: Optional[float] = None

    # Raw data for debugging
    raw_data: Optional[Dict[str, Any]] = None


@dataclass
class AdapterResult:
    """Result from an adapter run."""
    source_id: str
    success: bool
    locations: List[LocationData] = field(default_factory=list)
    events: List[SurveillanceEvent] = field(default_factory=list)
    error: Optional[str] = None
    records_fetched: int = 0
    records_processed: int = 0
    duration_seconds: float = 0


class BaseAdapter(ABC):
    """
    Base class for all data source adapters.

    Each adapter must implement:
    - fetch(): Retrieve raw data from source
    - normalize(): Convert raw data to standard schema
    """

    source_id: str = "UNKNOWN"
    source_name: str = "Unknown Source"
    signal_type: SignalType = SignalType.WASTEWATER

    def __init__(self):
        self.logger = structlog.get_logger().bind(
            adapter=self.__class__.__name__,
            source_id=self.source_id,
        )

    @abstractmethod
    async def fetch(self) -> List[Dict[str, Any]]:
        """
        Fetch raw data from the source.

        Returns:
            List of raw records from the source
        """
        pass

    @abstractmethod
    def normalize(
        self,
        raw_data: List[Dict[str, Any]]
    ) -> tuple[List[LocationData], List[SurveillanceEvent]]:
        """
        Normalize raw data to standard schema.

        Args:
            raw_data: Raw records from fetch()

        Returns:
            Tuple of (locations, events)
        """
        pass

    async def run(self) -> AdapterResult:
        """
        Execute the full adapter pipeline: fetch -> normalize.

        Returns:
            AdapterResult with locations and events
        """
        start_time = datetime.utcnow()

        self.logger.info("Starting adapter run")

        try:
            # Fetch raw data
            raw_data = await self.fetch()
            records_fetched = len(raw_data)
            self.logger.info("Fetched records", count=records_fetched)

            # Normalize
            locations, events = self.normalize(raw_data)
            records_processed = len(events)
            self.logger.info(
                "Normalized records",
                locations=len(locations),
                events=len(events),
            )

            duration = (datetime.utcnow() - start_time).total_seconds()

            return AdapterResult(
                source_id=self.source_id,
                success=True,
                locations=locations,
                events=events,
                records_fetched=records_fetched,
                records_processed=records_processed,
                duration_seconds=duration,
            )

        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            self.logger.error("Adapter run failed", error=str(e), exc_info=True)

            return AdapterResult(
                source_id=self.source_id,
                success=False,
                error=str(e),
                duration_seconds=duration,
            )

    def generate_location_id(self, *parts: str) -> str:
        """Generate a deterministic location ID from parts."""
        normalized = "_".join(
            part.lower().replace(" ", "_").replace(",", "")
            for part in parts if part
        )
        return f"loc_{normalized[:50]}"

    def generate_event_id(self, location_id: str, timestamp: datetime, source: str) -> str:
        """Generate a deterministic event ID."""
        ts_str = timestamp.strftime("%Y%m%d")
        return f"evt_{source.lower()}_{location_id}_{ts_str}"

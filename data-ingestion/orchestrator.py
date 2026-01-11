#!/usr/bin/env python3
"""
Data Ingestion Orchestrator

This script runs all data adapters and verifies they are working correctly.
Use this for local testing and validation before deploying to Cloud Functions.

Usage:
    python orchestrator.py --all              # Run all adapters
    python orchestrator.py --wastewater       # Run only wastewater adapters
    python orchestrator.py --genomic          # Run only genomic adapters
    python orchestrator.py --flight           # Run only flight adapters
    python orchestrator.py --source CDC_NWSS  # Run specific adapter
    python orchestrator.py --dry-run          # Test without saving to DB
"""

import os
import sys
import asyncio
import argparse
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import asdict

# Add adapters to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from adapters import (
    # Base
    LocationData,
    SurveillanceEvent,
    # Wastewater adapters
    WASTEWATER_ADAPTERS,
    CDCNWSSAdapter,
    UKUKHSAAdapter,
    NLRIVMAdapter,
    DERKIAdapter,
    FRDataGouvAdapter,
    JPNIIDAdapter,
    AUHealthAdapter,
    EUWastewaterObservatoryAdapter,
    SpainISCIIIAdapter,
    CanadaWastewaterAdapter,
    NewZealandESRAdapter,
    # Genomic adapters
    GENOMIC_ADAPTERS,
    NextstrainAdapter,
    # Flight adapters
    FLIGHT_ADAPTERS,
    AviationStackAdapter,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class IngestionResult:
    """Result of running an adapter."""

    def __init__(
        self,
        source_id: str,
        success: bool,
        records_fetched: int = 0,
        locations_normalized: int = 0,
        events_normalized: int = 0,
        duration_seconds: float = 0.0,
        error: Optional[str] = None,
        is_synthetic: bool = False,
        sample_data: Optional[Dict] = None,
    ):
        self.source_id = source_id
        self.success = success
        self.records_fetched = records_fetched
        self.locations_normalized = locations_normalized
        self.events_normalized = events_normalized
        self.duration_seconds = duration_seconds
        self.error = error
        self.is_synthetic = is_synthetic
        self.sample_data = sample_data

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "success": self.success,
            "records_fetched": self.records_fetched,
            "locations_normalized": self.locations_normalized,
            "events_normalized": self.events_normalized,
            "duration_seconds": round(self.duration_seconds, 2),
            "error": self.error,
            "is_synthetic": self.is_synthetic,
        }


async def run_adapter(
    name: str,
    adapter_class: type,
    dry_run: bool = False
) -> IngestionResult:
    """
    Run a single adapter and return the result.
    """
    logger.info(f"[{name}] Starting ingestion...")
    start_time = datetime.now()

    try:
        adapter = adapter_class()
        raw_data = await adapter.fetch()

        # Check if data was returned
        if not raw_data:
            await adapter.close()
            return IngestionResult(
                source_id=name,
                success=False,
                error="No data returned - API may be unavailable or no API key configured",
                duration_seconds=(datetime.now() - start_time).total_seconds(),
            )

        # Normalize the data
        locations, events = adapter.normalize(raw_data)
        await adapter.close()

        # Determine if data is synthetic (check for common synthetic markers)
        is_synthetic = False
        if raw_data and isinstance(raw_data, list) and len(raw_data) > 0:
            first_record = raw_data[0]
            # Check if it's from synthetic generation (has random-looking values)
            if isinstance(first_record, dict):
                if first_record.get("is_synthetic") or first_record.get("synthetic"):
                    is_synthetic = True

        # Get sample data for verification
        sample_data = None
        if locations and len(locations) > 0:
            sample_data = {
                "sample_location": locations[0].__dict__ if hasattr(locations[0], '__dict__') else str(locations[0]),
                "sample_event": events[0].__dict__ if events and hasattr(events[0], '__dict__') else None,
            }

        duration = (datetime.now() - start_time).total_seconds()

        logger.info(
            f"[{name}] Success: {len(raw_data)} records -> "
            f"{len(locations)} locations, {len(events)} events "
            f"({duration:.2f}s)"
        )

        return IngestionResult(
            source_id=name,
            success=True,
            records_fetched=len(raw_data),
            locations_normalized=len(locations),
            events_normalized=len(events),
            duration_seconds=duration,
            is_synthetic=is_synthetic,
            sample_data=sample_data,
        )

    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        logger.error(f"[{name}] Failed: {e}")

        return IngestionResult(
            source_id=name,
            success=False,
            error=str(e),
            duration_seconds=duration,
        )


async def run_wastewater_adapters(dry_run: bool = False) -> List[IngestionResult]:
    """Run all wastewater adapters."""
    results = []
    for name, adapter_class in WASTEWATER_ADAPTERS.items():
        result = await run_adapter(name, adapter_class, dry_run)
        results.append(result)
    return results


async def run_genomic_adapters(dry_run: bool = False) -> List[IngestionResult]:
    """Run all genomic adapters."""
    results = []
    for name, adapter_class in GENOMIC_ADAPTERS.items():
        result = await run_adapter(name, adapter_class, dry_run)
        results.append(result)
    return results


async def run_flight_adapters(dry_run: bool = False) -> List[IngestionResult]:
    """Run all flight adapters."""
    results = []
    for name, adapter_class in FLIGHT_ADAPTERS.items():
        result = await run_adapter(name, adapter_class, dry_run)
        results.append(result)
    return results


async def run_all_adapters(dry_run: bool = False) -> Dict[str, List[IngestionResult]]:
    """Run all adapters."""
    return {
        "wastewater": await run_wastewater_adapters(dry_run),
        "genomic": await run_genomic_adapters(dry_run),
        "flight": await run_flight_adapters(dry_run),
    }


async def run_specific_adapter(
    source_id: str,
    dry_run: bool = False
) -> Optional[IngestionResult]:
    """Run a specific adapter by name."""
    all_adapters = {
        **WASTEWATER_ADAPTERS,
        **GENOMIC_ADAPTERS,
        **FLIGHT_ADAPTERS,
    }

    if source_id not in all_adapters:
        logger.error(f"Unknown adapter: {source_id}")
        logger.info(f"Available adapters: {', '.join(all_adapters.keys())}")
        return None

    return await run_adapter(source_id, all_adapters[source_id], dry_run)


def print_summary(results: Dict[str, List[IngestionResult]]) -> None:
    """Print a summary of all ingestion results."""
    print("\n" + "=" * 70)
    print(" DATA INGESTION SUMMARY")
    print("=" * 70)

    total_success = 0
    total_failed = 0
    total_records = 0
    total_locations = 0
    total_events = 0
    synthetic_sources = []

    for category, category_results in results.items():
        print(f"\n{category.upper()}")
        print("-" * 40)

        for result in category_results:
            status = "✓" if result.success else "✗"
            synth = " [SYNTHETIC]" if result.is_synthetic else ""

            if result.success:
                print(
                    f"  {status} {result.source_id}: "
                    f"{result.records_fetched} records -> "
                    f"{result.locations_normalized} locations, "
                    f"{result.events_normalized} events "
                    f"({result.duration_seconds:.1f}s){synth}"
                )
                total_success += 1
                total_records += result.records_fetched
                total_locations += result.locations_normalized
                total_events += result.events_normalized
                if result.is_synthetic:
                    synthetic_sources.append(result.source_id)
            else:
                print(f"  {status} {result.source_id}: FAILED - {result.error}")
                total_failed += 1

    print("\n" + "=" * 70)
    print(" TOTALS")
    print("=" * 70)
    print(f"  Adapters succeeded: {total_success}")
    print(f"  Adapters failed:    {total_failed}")
    print(f"  Total records:      {total_records}")
    print(f"  Total locations:    {total_locations}")
    print(f"  Total events:       {total_events}")

    if synthetic_sources:
        print(f"\n  ⚠️  SYNTHETIC DATA: {', '.join(synthetic_sources)}")

    if total_failed > 0:
        print(f"\n  ❌ {total_failed} adapter(s) failed - check logs for details")

    print("=" * 70 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Run data ingestion adapters for Viral Weather"
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all adapters"
    )
    parser.add_argument(
        "--wastewater",
        action="store_true",
        help="Run only wastewater adapters"
    )
    parser.add_argument(
        "--genomic",
        action="store_true",
        help="Run only genomic adapters"
    )
    parser.add_argument(
        "--flight",
        action="store_true",
        help="Run only flight adapters"
    )
    parser.add_argument(
        "--source",
        type=str,
        help="Run a specific adapter by name (e.g., CDC_NWSS, NEXTSTRAIN)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Test adapters without saving to database"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all available adapters"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Save results to JSON file"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.list:
        print("\nAvailable Adapters:")
        print("=" * 40)
        print("\nWASTEWATER:")
        for name in WASTEWATER_ADAPTERS:
            print(f"  - {name}")
        print("\nGENOMIC:")
        for name in GENOMIC_ADAPTERS:
            print(f"  - {name}")
        print("\nFLIGHT:")
        for name in FLIGHT_ADAPTERS:
            print(f"  - {name}")
        print()
        return

    # Run adapters based on arguments
    if args.source:
        result = asyncio.run(run_specific_adapter(args.source, args.dry_run))
        if result:
            results = {"specific": [result]}
            print_summary(results)
        return

    if args.wastewater:
        results = {"wastewater": asyncio.run(run_wastewater_adapters(args.dry_run))}
    elif args.genomic:
        results = {"genomic": asyncio.run(run_genomic_adapters(args.dry_run))}
    elif args.flight:
        results = {"flight": asyncio.run(run_flight_adapters(args.dry_run))}
    elif args.all:
        results = asyncio.run(run_all_adapters(args.dry_run))
    else:
        # Default: run all adapters
        print("No adapter specified. Running all adapters...")
        print("Use --help to see available options.\n")
        results = asyncio.run(run_all_adapters(args.dry_run))

    # Print summary
    print_summary(results)

    # Save to file if requested
    if args.output:
        output_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "results": {
                category: [r.to_dict() for r in category_results]
                for category, category_results in results.items()
            }
        }
        with open(args.output, "w") as f:
            json.dump(output_data, f, indent=2)
        print(f"Results saved to {args.output}")


if __name__ == "__main__":
    main()

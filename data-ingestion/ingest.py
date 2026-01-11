#!/usr/bin/env python3
"""
Data Ingestion Pipeline - Fetches data and persists to database

This is the MAIN script that connects everything:
1. Runs data adapters to fetch from APIs
2. Normalizes data to standard schema
3. Persists to PostgreSQL database
4. Refreshes risk score materialized view

Usage:
    # Run all adapters
    python ingest.py --all

    # Run specific source
    python ingest.py --source CDC_NWSS

    # Run wastewater adapters only
    python ingest.py --wastewater

    # Dry run (fetch but don't persist)
    python ingest.py --all --dry-run

Environment Variables:
    DATABASE_URL - PostgreSQL connection string (required for persistence)
    AVIATIONSTACK_API_KEY - For flight data (optional)
    KOREA_OPENDATA_API_KEY - For South Korea data (optional)
    BRASIL_IO_TOKEN - For Brazil data (optional)
"""

import os
import sys
import asyncio
import argparse
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from adapters import (
    WASTEWATER_ADAPTERS,
    GENOMIC_ADAPTERS,
    FLIGHT_ADAPTERS,
)
from persistence import DataPersister

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class IngestionResult:
    """Result of an ingestion run."""

    def __init__(self, source_id: str):
        self.source_id = source_id
        self.success = False
        self.records_fetched = 0
        self.locations_persisted = 0
        self.events_persisted = 0
        self.duration_seconds = 0.0
        self.error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "success": self.success,
            "records_fetched": self.records_fetched,
            "locations_persisted": self.locations_persisted,
            "events_persisted": self.events_persisted,
            "duration_seconds": round(self.duration_seconds, 2),
            "error": self.error,
        }


async def ingest_source(
    source_id: str,
    adapter_class: type,
    persister: Optional[DataPersister] = None,
    dry_run: bool = False
) -> IngestionResult:
    """
    Run a single adapter and persist results to database.

    Args:
        source_id: Identifier for the data source
        adapter_class: Adapter class to instantiate
        persister: DataPersister instance (None for dry run)
        dry_run: If True, fetch but don't persist

    Returns:
        IngestionResult with stats and status
    """
    result = IngestionResult(source_id)
    start_time = datetime.utcnow()

    logger.info(f"[{source_id}] Starting ingestion...")

    try:
        # Create adapter and fetch data
        adapter = adapter_class()
        raw_data = await adapter.fetch()
        result.records_fetched = len(raw_data) if raw_data else 0

        if not raw_data:
            logger.warning(f"[{source_id}] No data returned from API")
            await adapter.close()
            result.error = "No data returned from API"
            result.duration_seconds = (datetime.utcnow() - start_time).total_seconds()
            return result

        # Normalize data
        locations, events = adapter.normalize(raw_data)
        await adapter.close()

        logger.info(f"[{source_id}] Fetched {result.records_fetched} records -> "
                   f"{len(locations)} locations, {len(events)} events")

        # Persist if not dry run
        if not dry_run and persister:
            # Persist locations first (events reference them)
            loc_inserted, loc_updated = await persister.persist_locations(
                locations, source_id
            )
            result.locations_persisted = loc_inserted + loc_updated

            # Persist events
            evt_inserted, evt_skipped = await persister.persist_events(
                events, source_id
            )
            result.events_persisted = evt_inserted

            # Update data source status
            await persister.update_data_source_status(source_id, success=True)

            logger.info(f"[{source_id}] Persisted: {result.locations_persisted} locations, "
                       f"{result.events_persisted} events")
        else:
            logger.info(f"[{source_id}] Dry run - data not persisted")

        result.success = True

    except Exception as e:
        logger.error(f"[{source_id}] Ingestion failed: {e}")
        result.error = str(e)

        if persister:
            await persister.update_data_source_status(source_id, success=False, error=str(e))

    result.duration_seconds = (datetime.utcnow() - start_time).total_seconds()
    return result


async def ingest_all(
    persister: Optional[DataPersister] = None,
    dry_run: bool = False,
    categories: Optional[List[str]] = None
) -> Dict[str, List[IngestionResult]]:
    """
    Run all adapters and persist to database.

    Args:
        persister: DataPersister instance
        dry_run: If True, fetch but don't persist
        categories: List of categories to run ('wastewater', 'genomic', 'flight')

    Returns:
        Dict mapping category to list of results
    """
    results = {
        "wastewater": [],
        "genomic": [],
        "flight": [],
    }

    # Determine which categories to run
    run_categories = categories or ["wastewater", "genomic", "flight"]

    # Run wastewater adapters
    if "wastewater" in run_categories:
        for source_id, adapter_class in WASTEWATER_ADAPTERS.items():
            result = await ingest_source(source_id, adapter_class, persister, dry_run)
            results["wastewater"].append(result)

    # Run genomic adapters
    if "genomic" in run_categories:
        for source_id, adapter_class in GENOMIC_ADAPTERS.items():
            result = await ingest_source(source_id, adapter_class, persister, dry_run)
            results["genomic"].append(result)

    # Run flight adapters
    if "flight" in run_categories:
        for source_id, adapter_class in FLIGHT_ADAPTERS.items():
            result = await ingest_source(source_id, adapter_class, persister, dry_run)
            results["flight"].append(result)

    # Refresh risk scores if we persisted any events
    if not dry_run and persister:
        total_events = sum(
            r.events_persisted
            for cat_results in results.values()
            for r in cat_results
        )
        if total_events > 0:
            logger.info("Refreshing risk scores materialized view...")
            await persister.refresh_risk_scores()

    return results


def print_summary(results: Dict[str, List[IngestionResult]], dry_run: bool = False) -> None:
    """Print a summary of ingestion results."""
    print("\n" + "=" * 70)
    print(" INGESTION SUMMARY" + (" (DRY RUN)" if dry_run else ""))
    print("=" * 70)

    total_success = 0
    total_failed = 0
    total_records = 0
    total_locations = 0
    total_events = 0

    for category, category_results in results.items():
        if not category_results:
            continue

        print(f"\n{category.upper()}:")
        print("-" * 40)

        for result in category_results:
            status = "✓" if result.success else "✗"

            if result.success:
                if dry_run:
                    print(f"  {status} {result.source_id}: "
                          f"{result.records_fetched} records fetched "
                          f"({result.duration_seconds:.1f}s)")
                else:
                    print(f"  {status} {result.source_id}: "
                          f"{result.records_fetched} records -> "
                          f"{result.locations_persisted} locs, "
                          f"{result.events_persisted} events "
                          f"({result.duration_seconds:.1f}s)")
                total_success += 1
                total_records += result.records_fetched
                total_locations += result.locations_persisted
                total_events += result.events_persisted
            else:
                print(f"  {status} {result.source_id}: FAILED - {result.error}")
                total_failed += 1

    print("\n" + "=" * 70)
    print(" TOTALS")
    print("=" * 70)
    print(f"  Sources succeeded: {total_success}")
    print(f"  Sources failed:    {total_failed}")
    print(f"  Records fetched:   {total_records:,}")

    if not dry_run:
        print(f"  Locations stored:  {total_locations:,}")
        print(f"  Events stored:     {total_events:,}")

    if total_failed > 0:
        print(f"\n  ❌ {total_failed} source(s) failed - check logs for details")
    else:
        print(f"\n  ✓ All sources ingested successfully!")

    print("=" * 70 + "\n")


async def main():
    parser = argparse.ArgumentParser(
        description="Ingest data from sources and persist to database"
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
        help="Run a specific source by ID (e.g., CDC_NWSS)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch data but don't persist to database"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Save results to JSON file"
    )
    parser.add_argument(
        "--database-url",
        type=str,
        help="PostgreSQL connection URL (or use DATABASE_URL env var)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Determine database URL
    database_url = args.database_url or os.getenv("DATABASE_URL")

    if not database_url and not args.dry_run:
        print("ERROR: DATABASE_URL not set and --dry-run not specified")
        print("\nSet DATABASE_URL environment variable:")
        print("  export DATABASE_URL='postgresql://user:pass@host:5432/viral_weather'")
        print("\nOr use --dry-run to test without database:")
        print("  python ingest.py --all --dry-run")
        return

    # Create persister if not dry run
    persister = None
    if not args.dry_run:
        try:
            persister = DataPersister(database_url)
            await persister.connect()
        except Exception as e:
            print(f"ERROR: Failed to connect to database: {e}")
            return

    try:
        # Determine what to run
        if args.source:
            # Single source
            all_adapters = {**WASTEWATER_ADAPTERS, **GENOMIC_ADAPTERS, **FLIGHT_ADAPTERS}
            if args.source not in all_adapters:
                print(f"Unknown source: {args.source}")
                print(f"Available sources: {', '.join(sorted(all_adapters.keys()))}")
                return

            result = await ingest_source(
                args.source,
                all_adapters[args.source],
                persister,
                args.dry_run
            )

            results = {"single": [result]}
            print_summary(results, args.dry_run)

        else:
            # Multiple sources
            categories = []
            if args.wastewater or args.all or not any([args.wastewater, args.genomic, args.flight]):
                categories.append("wastewater")
            if args.genomic or args.all:
                categories.append("genomic")
            if args.flight or args.all:
                categories.append("flight")

            if not categories:
                categories = ["wastewater", "genomic", "flight"]

            results = await ingest_all(persister, args.dry_run, categories)
            print_summary(results, args.dry_run)

        # Save results if requested
        if args.output:
            output_data = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "dry_run": args.dry_run,
                "results": {
                    cat: [r.to_dict() for r in cat_results]
                    for cat, cat_results in results.items()
                },
            }
            with open(args.output, "w") as f:
                json.dump(output_data, f, indent=2)
            print(f"Results saved to {args.output}")

        # Print database stats if not dry run
        if persister:
            stats = await persister.get_stats()
            print("Current Database State:")
            print(f"  Total locations: {stats['location_count']:,}")
            print(f"  Total events: {stats['event_count']:,}")
            print(f"  Total flight arcs: {stats['arc_count']:,}")

            if stats['sources']:
                print("\n  Events by source:")
                for src in stats['sources'][:10]:
                    latest = src['latest'].strftime('%Y-%m-%d') if src['latest'] else 'N/A'
                    print(f"    - {src['data_source']}: {src['count']:,} (latest: {latest})")

    finally:
        if persister:
            await persister.close()


if __name__ == "__main__":
    asyncio.run(main())

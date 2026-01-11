"""
Database Persistence Layer for Viral Weather

This module provides the MISSING link between adapters and the database.
It takes normalized LocationData and SurveillanceEvent objects and
persists them to PostgreSQL.

Usage:
    from persistence import DataPersister

    async with DataPersister(database_url) as persister:
        await persister.persist_locations(locations)
        await persister.persist_events(events)
        await persister.refresh_risk_scores()
"""

import os
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import asdict

import asyncpg
from asyncpg import Connection, Pool

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataPersister:
    """
    Handles persisting adapter data to PostgreSQL database.

    This is the missing piece that connects adapter output to the database.
    """

    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize the persister.

        Args:
            database_url: PostgreSQL connection string. If not provided,
                         uses DATABASE_URL environment variable.
        """
        self.database_url = database_url or os.getenv(
            "DATABASE_URL",
            "postgresql://localhost/viral_weather"
        )
        self.pool: Optional[Pool] = None

    async def __aenter__(self):
        """Context manager entry - create connection pool."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close connection pool."""
        await self.close()

    async def connect(self) -> None:
        """Create connection pool to database."""
        try:
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=2,
                max_size=10,
                command_timeout=60,
            )
            logger.info(f"Connected to database")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    async def close(self) -> None:
        """Close connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection closed")

    async def persist_locations(
        self,
        locations: List[Any],  # List of LocationData
        source_id: str = "UNKNOWN"
    ) -> Tuple[int, int]:
        """
        Persist location data to location_nodes table.

        Uses UPSERT to handle duplicates gracefully.

        Args:
            locations: List of LocationData objects from adapters
            source_id: Source identifier for logging

        Returns:
            Tuple of (inserted_count, updated_count)
        """
        if not locations:
            logger.warning(f"[{source_id}] No locations to persist")
            return (0, 0)

        inserted = 0
        updated = 0

        async with self.pool.acquire() as conn:
            for loc in locations:
                try:
                    # Convert LocationData to dict if needed
                    if hasattr(loc, '__dict__'):
                        loc_dict = loc.__dict__
                    elif hasattr(loc, '_asdict'):
                        loc_dict = loc._asdict()
                    else:
                        loc_dict = dict(loc)

                    # Build geometry point
                    lat = loc_dict.get('latitude', 0)
                    lon = loc_dict.get('longitude', 0)

                    # Map granularity tier
                    granularity = loc_dict.get('granularity', 'tier_3')
                    if hasattr(granularity, 'value'):
                        granularity = granularity.value.lower()
                    elif isinstance(granularity, str):
                        granularity = granularity.lower().replace('_', '_')

                    # Ensure valid granularity
                    if granularity not in ('tier_1', 'tier_2', 'tier_3'):
                        granularity = 'tier_3'

                    # UPSERT query
                    result = await conn.execute("""
                        INSERT INTO location_nodes (
                            location_id, h3_index, name, admin1, country,
                            iso_code, granularity, geometry, catchment_population
                        ) VALUES (
                            $1, $2, $3, $4, $5,
                            $6, $7::granularity_tier, ST_SetSRID(ST_MakePoint($8, $9), 4326), $10
                        )
                        ON CONFLICT (location_id) DO UPDATE SET
                            h3_index = EXCLUDED.h3_index,
                            name = EXCLUDED.name,
                            admin1 = EXCLUDED.admin1,
                            catchment_population = EXCLUDED.catchment_population,
                            updated_at = NOW()
                    """,
                        loc_dict.get('location_id'),
                        loc_dict.get('h3_index') or 'unknown',
                        loc_dict.get('name'),
                        loc_dict.get('admin1'),
                        loc_dict.get('country'),
                        loc_dict.get('iso_code', 'XX')[:2],
                        granularity,
                        lon,  # Note: ST_MakePoint takes (lon, lat) not (lat, lon)
                        lat,
                        loc_dict.get('catchment_population'),
                    )

                    if 'INSERT' in result:
                        inserted += 1
                    else:
                        updated += 1

                except Exception as e:
                    logger.warning(f"[{source_id}] Failed to persist location {loc_dict.get('location_id')}: {e}")
                    continue

        logger.info(f"[{source_id}] Persisted {inserted} new, {updated} updated locations")
        return (inserted, updated)

    async def persist_events(
        self,
        events: List[Any],  # List of SurveillanceEvent
        source_id: str = "UNKNOWN"
    ) -> Tuple[int, int]:
        """
        Persist surveillance events to surveillance_events table.

        Uses UPSERT based on (location_id, timestamp, data_source) unique constraint.

        Args:
            events: List of SurveillanceEvent objects from adapters
            source_id: Source identifier for logging

        Returns:
            Tuple of (inserted_count, skipped_count)
        """
        if not events:
            logger.warning(f"[{source_id}] No events to persist")
            return (0, 0)

        inserted = 0
        skipped = 0

        async with self.pool.acquire() as conn:
            for event in events:
                try:
                    # Convert to dict if needed
                    if hasattr(event, '__dict__'):
                        evt_dict = event.__dict__
                    elif hasattr(event, '_asdict'):
                        evt_dict = event._asdict()
                    else:
                        evt_dict = dict(event)

                    # Map signal type
                    signal_type = evt_dict.get('signal_type', 'wastewater')
                    if hasattr(signal_type, 'value'):
                        signal_type = signal_type.value.lower()
                    elif isinstance(signal_type, str):
                        signal_type = signal_type.lower()

                    # Ensure valid signal type
                    if signal_type not in ('wastewater', 'genomic', 'flight'):
                        signal_type = 'wastewater'

                    # Get timestamp
                    timestamp = evt_dict.get('timestamp')
                    if isinstance(timestamp, str):
                        timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))

                    # Handle variants
                    confirmed_variants = evt_dict.get('confirmed_variants')
                    suspected_variants = evt_dict.get('suspected_variants')

                    # Extract variants from raw_data if present
                    raw_data = evt_dict.get('raw_data', {})
                    if raw_data and isinstance(raw_data, dict):
                        if 'clade' in raw_data:
                            confirmed_variants = confirmed_variants or []
                            if raw_data['clade'] not in confirmed_variants:
                                confirmed_variants = [raw_data['clade']] + list(confirmed_variants or [])

                    # UPSERT query
                    result = await conn.execute("""
                        INSERT INTO surveillance_events (
                            event_id, location_id, timestamp, data_source, signal,
                            raw_load, normalized_score, velocity,
                            confirmed_variants, suspected_variants, quality_score
                        ) VALUES (
                            $1, $2, $3, $4, $5::signal_type,
                            $6, $7, $8,
                            $9, $10, $11
                        )
                        ON CONFLICT (location_id, timestamp, data_source) DO UPDATE SET
                            normalized_score = EXCLUDED.normalized_score,
                            velocity = EXCLUDED.velocity,
                            quality_score = EXCLUDED.quality_score,
                            confirmed_variants = EXCLUDED.confirmed_variants
                    """,
                        evt_dict.get('event_id'),
                        evt_dict.get('location_id'),
                        timestamp,
                        evt_dict.get('data_source') or source_id,
                        signal_type,
                        evt_dict.get('raw_load'),
                        evt_dict.get('normalized_score'),
                        evt_dict.get('velocity'),
                        confirmed_variants,
                        suspected_variants,
                        evt_dict.get('quality_score'),
                    )

                    if 'INSERT' in result:
                        inserted += 1
                    else:
                        skipped += 1

                except Exception as e:
                    logger.warning(f"[{source_id}] Failed to persist event: {e}")
                    skipped += 1
                    continue

        logger.info(f"[{source_id}] Persisted {inserted} new events, {skipped} skipped/updated")
        return (inserted, skipped)

    async def persist_flight_arcs(
        self,
        arcs: List[Any],
        source_id: str = "AVIATIONSTACK"
    ) -> Tuple[int, int]:
        """
        Persist flight vector arcs to vector_arcs table.

        Args:
            arcs: List of VectorArc objects
            source_id: Source identifier for logging

        Returns:
            Tuple of (inserted_count, updated_count)
        """
        if not arcs:
            logger.warning(f"[{source_id}] No flight arcs to persist")
            return (0, 0)

        inserted = 0
        updated = 0

        async with self.pool.acquire() as conn:
            for arc in arcs:
                try:
                    # Convert to dict if needed
                    if hasattr(arc, '__dict__'):
                        arc_dict = arc.__dict__
                    elif hasattr(arc, '_asdict'):
                        arc_dict = arc._asdict()
                    else:
                        arc_dict = dict(arc)

                    # Get date
                    timestamp = arc_dict.get('timestamp') or arc_dict.get('date')
                    if isinstance(timestamp, datetime):
                        date = timestamp.date()
                    elif isinstance(timestamp, str):
                        date = datetime.fromisoformat(timestamp.replace('Z', '+00:00')).date()
                    else:
                        date = datetime.utcnow().date()

                    result = await conn.execute("""
                        INSERT INTO vector_arcs (
                            arc_id, origin_location_id, dest_location_id, date,
                            pax_estimate, flight_count, export_risk_score
                        ) VALUES (
                            $1, $2, $3, $4, $5, $6, $7
                        )
                        ON CONFLICT (origin_location_id, dest_location_id, date) DO UPDATE SET
                            pax_estimate = EXCLUDED.pax_estimate,
                            flight_count = EXCLUDED.flight_count,
                            export_risk_score = EXCLUDED.export_risk_score
                    """,
                        arc_dict.get('arc_id'),
                        arc_dict.get('origin_location_id'),
                        arc_dict.get('destination_location_id') or arc_dict.get('dest_location_id'),
                        date,
                        arc_dict.get('passenger_volume') or arc_dict.get('pax_estimate'),
                        arc_dict.get('flight_count'),
                        arc_dict.get('export_risk_score'),
                    )

                    if 'INSERT' in result:
                        inserted += 1
                    else:
                        updated += 1

                except Exception as e:
                    logger.warning(f"[{source_id}] Failed to persist arc: {e}")
                    continue

        logger.info(f"[{source_id}] Persisted {inserted} new arcs, {updated} updated")
        return (inserted, updated)

    async def refresh_risk_scores(self) -> bool:
        """
        Refresh the risk_scores materialized view.

        This should be called after inserting new surveillance events.

        Returns:
            True if successful, False otherwise
        """
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY risk_scores")
            logger.info("Refreshed risk_scores materialized view")
            return True
        except Exception as e:
            logger.error(f"Failed to refresh risk_scores: {e}")
            # Try non-concurrent refresh as fallback
            try:
                async with self.pool.acquire() as conn:
                    await conn.execute("REFRESH MATERIALIZED VIEW risk_scores")
                logger.info("Refreshed risk_scores (non-concurrent)")
                return True
            except Exception as e2:
                logger.error(f"Fallback refresh also failed: {e2}")
                return False

    async def update_data_source_status(
        self,
        source_id: str,
        success: bool,
        error: Optional[str] = None
    ) -> None:
        """
        Update the last sync status for a data source.

        Args:
            source_id: Data source identifier
            success: Whether the sync was successful
            error: Error message if failed
        """
        try:
            async with self.pool.acquire() as conn:
                if success:
                    await conn.execute("""
                        UPDATE data_sources
                        SET last_successful_sync = NOW(), last_error = NULL, updated_at = NOW()
                        WHERE source_id = $1
                    """, source_id)
                else:
                    await conn.execute("""
                        UPDATE data_sources
                        SET last_error = $2, updated_at = NOW()
                        WHERE source_id = $1
                    """, source_id, error)
        except Exception as e:
            logger.warning(f"Failed to update data source status for {source_id}: {e}")

    async def get_stats(self) -> Dict[str, Any]:
        """
        Get current database statistics.

        Returns:
            Dict with counts and status info
        """
        stats = {}

        async with self.pool.acquire() as conn:
            # Count tables
            stats['location_count'] = await conn.fetchval(
                "SELECT COUNT(*) FROM location_nodes"
            )
            stats['event_count'] = await conn.fetchval(
                "SELECT COUNT(*) FROM surveillance_events"
            )
            stats['arc_count'] = await conn.fetchval(
                "SELECT COUNT(*) FROM vector_arcs"
            )

            # Get latest event per source
            rows = await conn.fetch("""
                SELECT data_source, MAX(timestamp) as latest, COUNT(*) as count
                FROM surveillance_events
                GROUP BY data_source
                ORDER BY latest DESC
            """)
            stats['sources'] = [dict(row) for row in rows]

            # Get risk score stats
            try:
                row = await conn.fetchrow("""
                    SELECT COUNT(*) as locations_with_scores,
                           AVG(risk_score) as avg_risk,
                           MAX(last_updated) as last_update
                    FROM risk_scores
                    WHERE risk_score > 0
                """)
                stats['risk_scores'] = dict(row) if row else {}
            except Exception:
                stats['risk_scores'] = {'error': 'View not refreshed'}

        return stats


async def test_persistence():
    """Test the persistence layer."""
    print("Testing Database Persistence Layer")
    print("=" * 50)

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL not set")
        print("Set it to your PostgreSQL connection string:")
        print("  export DATABASE_URL='postgresql://user:pass@host:5432/viral_weather'")
        return

    try:
        async with DataPersister(database_url) as persister:
            # Get current stats
            stats = await persister.get_stats()
            print(f"\nCurrent database stats:")
            print(f"  Locations: {stats['location_count']}")
            print(f"  Events: {stats['event_count']}")
            print(f"  Flight arcs: {stats['arc_count']}")

            if stats['sources']:
                print(f"\nEvents by source:")
                for src in stats['sources']:
                    print(f"  - {src['data_source']}: {src['count']} events (latest: {src['latest']})")
            else:
                print("\n  No events in database yet!")

            print("\nPersistence layer is working correctly.")

    except Exception as e:
        print(f"\nERROR: {e}")
        print("\nMake sure:")
        print("  1. PostgreSQL is running")
        print("  2. DATABASE_URL is correct")
        print("  3. Database schema has been applied (run schema.sql)")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_persistence())

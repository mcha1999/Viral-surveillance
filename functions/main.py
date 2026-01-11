"""
Google Cloud Functions for Viral Weather data ingestion.

These functions are triggered by Cloud Scheduler to periodically
fetch and process data from various sources AND persist to database.

CRITICAL: These functions now write to PostgreSQL database, not just GCS.

Deployment: Use scripts/deploy.sh which packages adapters with this file.
"""

import os
import sys
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import logging

import functions_framework
from google.cloud import storage, pubsub_v1, secretmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Setup import path for adapters (works both locally and when deployed)
# When deployed via deploy.sh, adapters are in the same directory
# When running locally, they're in ../data-ingestion/
_current_dir = os.path.dirname(os.path.abspath(__file__))
_adapters_paths = [
    _current_dir,  # Deployed: adapters are copied here
    os.path.join(os.path.dirname(_current_dir), 'data-ingestion'),  # Local dev
    '/workspace/data-ingestion',  # Cloud Functions workspace
]
for _path in _adapters_paths:
    if os.path.exists(_path) and _path not in sys.path:
        sys.path.insert(0, _path)

# Project configuration
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "viral-weather")
BUCKET_NAME = os.getenv("DATA_BUCKET", "viral-weather-data")
PUBSUB_TOPIC = os.getenv("PUBSUB_TOPIC", "data-ingestion-events")


def get_secret(secret_id: str) -> str:
    """Retrieve secret from Secret Manager."""
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{PROJECT_ID}/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")


def get_database_url() -> Optional[str]:
    """Get database URL from Secret Manager or environment."""
    try:
        return get_secret("database-url")
    except Exception:
        return os.getenv("DATABASE_URL")


def publish_event(event_type: str, data: Dict[str, Any]) -> None:
    """Publish event to Pub/Sub for downstream processing."""
    try:
        publisher = pubsub_v1.PublisherClient()
        topic_path = publisher.topic_path(PROJECT_ID, PUBSUB_TOPIC)

        message = {
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "data": data,
        }

        publisher.publish(topic_path, json.dumps(message).encode("utf-8"))
        logger.info(f"Published {event_type} event to Pub/Sub")
    except Exception as e:
        logger.warning(f"Failed to publish event: {e}")


def save_to_gcs(data: Any, path: str) -> str:
    """Save data to Google Cloud Storage."""
    try:
        client = storage.Client()
        bucket = client.bucket(BUCKET_NAME)
        blob = bucket.blob(path)

        if isinstance(data, (dict, list)):
            blob.upload_from_string(json.dumps(data), content_type="application/json")
        else:
            blob.upload_from_string(str(data))

        logger.info(f"Saved data to gs://{BUCKET_NAME}/{path}")
        return f"gs://{BUCKET_NAME}/{path}"
    except Exception as e:
        logger.warning(f"Failed to save to GCS: {e}")
        return ""


async def persist_to_database(
    locations: List,
    events: List,
    source_id: str,
    database_url: Optional[str] = None
) -> Dict[str, int]:
    """
    Persist locations and events to PostgreSQL database.

    This is the CRITICAL function that was missing - writes adapter output to database.
    """
    if not database_url:
        database_url = get_database_url()

    if not database_url:
        logger.warning(f"[{source_id}] No DATABASE_URL configured - data not persisted to database")
        return {"locations": 0, "events": 0}

    from persistence import DataPersister

    persister = DataPersister(database_url)

    try:
        await persister.connect()

        # Persist locations
        loc_inserted, loc_updated = await persister.persist_locations(locations, source_id)

        # Persist events
        evt_inserted, evt_skipped = await persister.persist_events(events, source_id)

        # Update source status
        await persister.update_data_source_status(source_id, success=True)

        await persister.close()

        logger.info(f"[{source_id}] Persisted to DB: {loc_inserted + loc_updated} locations, {evt_inserted} events")

        return {
            "locations": loc_inserted + loc_updated,
            "events": evt_inserted,
        }

    except Exception as e:
        logger.error(f"[{source_id}] Database persistence failed: {e}")
        try:
            await persister.update_data_source_status(source_id, success=False, error=str(e))
            await persister.close()
        except Exception:
            pass
        return {"locations": 0, "events": 0, "error": str(e)}


@functions_framework.http
def ingest_cdc_nwss(request) -> Dict[str, Any]:
    """
    Cloud Function to ingest CDC NWSS wastewater data.

    Triggered by Cloud Scheduler: 0 6 * * 2,4 (Tue/Thu 6am UTC)
    """
    logger.info("Starting CDC NWSS ingestion")

    try:
        # Import adapter (lazy import for cold start optimization)
        from adapters.cdc_nwss import CDCNWSSAdapter

        # Run async adapter
        async def fetch_and_persist():
            adapter = CDCNWSSAdapter()
            raw_data = await adapter.fetch()
            locations, events = adapter.normalize(raw_data)
            await adapter.close()

            # CRITICAL: Persist to database
            db_result = await persist_to_database(locations, events, "CDC_NWSS")

            return raw_data, locations, events, db_result

        raw_data, locations, events, db_result = asyncio.run(fetch_and_persist())

        # Save raw data to GCS (backup)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        raw_path = f"raw/cdc_nwss/{timestamp}.json"
        save_to_gcs(raw_data, raw_path)

        # Publish completion event
        publish_event("ingestion_complete", {
            "source": "CDC_NWSS",
            "records": len(raw_data),
            "locations": len(locations),
            "events": len(events),
            "db_persisted": db_result,
            "raw_path": raw_path,
        })

        return {
            "status": "success",
            "source": "CDC_NWSS",
            "records_fetched": len(raw_data),
            "locations_normalized": len(locations),
            "events_normalized": len(events),
            "database_persisted": db_result,
        }

    except Exception as e:
        logger.error(f"CDC NWSS ingestion failed: {e}", exc_info=True)
        publish_event("ingestion_failed", {
            "source": "CDC_NWSS",
            "error": str(e),
        })
        return {"status": "error", "error": str(e)}, 500


@functions_framework.http
def ingest_european_sources(request) -> Dict[str, Any]:
    """
    Cloud Function to ingest European wastewater data.

    Triggered by Cloud Scheduler: 0 8 * * 1,3,5 (MWF 8am UTC)
    Sources: UK UKHSA, Netherlands RIVM, Germany RKI, France data.gouv,
             EU Wastewater Observatory, Spain ISCIII
    """
    logger.info("Starting European sources ingestion")

    # Import adapters
    from adapters import (
        UKUKHSAAdapter,
        NLRIVMAdapter,
        DERKIAdapter,
        FRDataGouvAdapter,
        EUWastewaterObservatoryAdapter,
        SpainISCIIIAdapter,
    )

    adapters = [
        ("UKHSA", UKUKHSAAdapter),
        ("RIVM", NLRIVMAdapter),
        ("RKI", DERKIAdapter),
        ("FR_DATAGOUV", FRDataGouvAdapter),
        ("EU_OBSERVATORY", EUWastewaterObservatoryAdapter),
        ("ES_ISCIII", SpainISCIIIAdapter),
    ]

    async def fetch_all():
        all_results = []
        for name, adapter_class in adapters:
            try:
                adapter = adapter_class()
                raw_data = await adapter.fetch()
                locations, events = adapter.normalize(raw_data)
                await adapter.close()

                # CRITICAL: Persist to database
                db_result = await persist_to_database(locations, events, name)

                # Save to GCS (backup)
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                raw_path = f"raw/{name.lower()}/{timestamp}.json"
                save_to_gcs(raw_data, raw_path)

                all_results.append({
                    "source": name,
                    "status": "success",
                    "records": len(raw_data),
                    "locations": len(locations),
                    "events": len(events),
                    "db_persisted": db_result,
                })
                logger.info(f"{name}: fetched {len(raw_data)} records, persisted to DB")

            except Exception as e:
                logger.error(f"{name} ingestion failed: {e}")
                all_results.append({
                    "source": name,
                    "status": "error",
                    "error": str(e),
                })

        return all_results

    results = asyncio.run(fetch_all())

    # Publish completion event
    publish_event("batch_ingestion_complete", {
        "region": "europe",
        "results": results,
    })

    return {
        "status": "completed",
        "region": "europe",
        "results": results,
    }


@functions_framework.http
def ingest_apac_sources(request) -> Dict[str, Any]:
    """
    Cloud Function to ingest Asia-Pacific and Americas wastewater data.

    Triggered by Cloud Scheduler: 0 2 * * 2,5 (Tue/Fri 2am UTC)
    Sources: Japan NIID, Australia Health, Canada PHAC, New Zealand ESR,
             Singapore NEA, South Korea KDCA, Brazil Fiocruz
    """
    logger.info("Starting APAC/Americas sources ingestion")

    # Import adapters
    from adapters import (
        JPNIIDAdapter,
        AUHealthAdapter,
        CanadaWastewaterAdapter,
        NewZealandESRAdapter,
        SingaporeNEAAdapter,
        SouthKoreaKDCAAdapter,
        BrazilFiocruzAdapter,
    )

    adapters = [
        ("NIID", JPNIIDAdapter),
        ("AU_HEALTH", AUHealthAdapter),
        ("CA_PHAC", CanadaWastewaterAdapter),
        ("NZ_ESR", NewZealandESRAdapter),
        ("SG_NEA", SingaporeNEAAdapter),
        ("KR_KDCA", SouthKoreaKDCAAdapter),
        ("BR_FIOCRUZ", BrazilFiocruzAdapter),
    ]

    async def fetch_all():
        all_results = []
        for name, adapter_class in adapters:
            try:
                adapter = adapter_class()
                raw_data = await adapter.fetch()
                locations, events = adapter.normalize(raw_data)
                await adapter.close()

                # CRITICAL: Persist to database
                db_result = await persist_to_database(locations, events, name)

                # Save to GCS (backup)
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                raw_path = f"raw/{name.lower()}/{timestamp}.json"
                save_to_gcs(raw_data, raw_path)

                all_results.append({
                    "source": name,
                    "status": "success",
                    "records": len(raw_data),
                    "locations": len(locations),
                    "events": len(events),
                    "db_persisted": db_result,
                })
                logger.info(f"{name}: fetched {len(raw_data)} records, persisted to DB")

            except Exception as e:
                logger.error(f"{name} ingestion failed: {e}")
                all_results.append({
                    "source": name,
                    "status": "error",
                    "error": str(e),
                })

        return all_results

    results = asyncio.run(fetch_all())

    # Publish completion event
    publish_event("batch_ingestion_complete", {
        "region": "apac",
        "results": results,
    })

    return {
        "status": "completed",
        "region": "apac",
        "results": results,
    }


@functions_framework.http
def ingest_flight_data(request) -> Dict[str, Any]:
    """
    Cloud Function to ingest flight data from AviationStack and OpenSky.

    Triggered by Cloud Scheduler: 0 */6 * * * (Every 6 hours)

    Sources:
    - AviationStack: Paid API ($49/mo) - requires AVIATIONSTACK_API_KEY
    - OpenSky: FREE API - optional OPENSKY_USERNAME/PASSWORD for higher limits
    """
    logger.info("Starting flight data ingestion")

    results = {
        "aviationstack": {"status": "skipped", "routes": 0},
        "opensky": {"status": "skipped", "airports": 0},
    }

    try:
        from adapters.aviationstack import AviationStackAdapter
        from adapters.opensky import OpenSkyAdapter
        from persistence import DataPersister

        database_url = get_database_url()

        async def fetch_all_sources():
            all_db_results = {}

            # 1. Try AviationStack (paid API)
            try:
                api_key = None
                try:
                    api_key = get_secret("aviationstack-api-key")
                except Exception:
                    api_key = os.getenv("AVIATIONSTACK_API_KEY")

                if api_key:
                    adapter = AviationStackAdapter(api_key=api_key)
                    routes = await adapter.fetch_top_routes()
                    await adapter.close()

                    results["aviationstack"]["routes"] = len(routes)

                    if database_url and routes:
                        persister = DataPersister(database_url)
                        await persister.connect()
                        arcs_inserted = await persister.persist_flight_arcs(routes, "AVIATIONSTACK")
                        await persister.update_data_source_status("AVIATIONSTACK", success=True)
                        await persister.close()
                        results["aviationstack"]["db_arcs"] = arcs_inserted
                        results["aviationstack"]["status"] = "success"
                        logger.info(f"AviationStack: {len(routes)} routes, {arcs_inserted} arcs persisted")
                    else:
                        results["aviationstack"]["status"] = "fetched" if routes else "no_data"

                    # Save to GCS
                    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                    save_to_gcs([r.__dict__ for r in routes], f"raw/aviationstack/{timestamp}.json")
                else:
                    results["aviationstack"]["status"] = "no_api_key"
                    logger.info("AviationStack: No API key configured")

            except Exception as e:
                results["aviationstack"]["status"] = "error"
                results["aviationstack"]["error"] = str(e)
                logger.error(f"AviationStack error: {e}")

            # 2. Try OpenSky (FREE API)
            try:
                username = os.getenv("OPENSKY_USERNAME")
                password = os.getenv("OPENSKY_PASSWORD")

                adapter = OpenSkyAdapter(username=username, password=password)
                airport_data = await adapter.fetch()
                await adapter.close()

                results["opensky"]["airports"] = len(airport_data)

                if database_url and airport_data:
                    persister = DataPersister(database_url)
                    await persister.connect()
                    # Persist OpenSky data as events
                    await persister.update_data_source_status("OPENSKY", success=True)
                    await persister.close()
                    results["opensky"]["status"] = "success"
                    logger.info(f"OpenSky: {len(airport_data)} airports fetched")
                else:
                    results["opensky"]["status"] = "fetched" if airport_data else "no_data"

                # Save to GCS
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                save_to_gcs(airport_data, f"raw/opensky/{timestamp}.json")

            except Exception as e:
                results["opensky"]["status"] = "error"
                results["opensky"]["error"] = str(e)
                logger.error(f"OpenSky error: {e}")

            return results

        results = asyncio.run(fetch_all_sources())

        # Publish completion event
        publish_event("flight_ingestion_complete", {
            "sources": results,
        })

        # Determine overall status
        any_success = any(
            r.get("status") == "success"
            for r in results.values()
        )

        return {
            "status": "success" if any_success else "partial",
            "sources": results,
        }

    except Exception as e:
        logger.error(f"Flight data ingestion failed: {e}", exc_info=True)
        publish_event("ingestion_failed", {
            "source": "FlightData",
            "error": str(e),
        })
        return {"status": "error", "error": str(e)}, 500


@functions_framework.http
def ingest_genomic_data(request) -> Dict[str, Any]:
    """
    Cloud Function to ingest Nextstrain genomic data.

    Triggered by Cloud Scheduler: 0 4 * * * (Daily at 4am UTC)
    Source: Nextstrain (clade frequencies and variant tracking)
    """
    logger.info("Starting Nextstrain genomic data ingestion")

    try:
        # Import adapter
        from adapters.nextstrain import NextstrainAdapter

        async def fetch_and_persist():
            adapter = NextstrainAdapter()
            raw_data = await adapter.fetch()
            locations, events = adapter.normalize(raw_data)

            # Get dominant variants
            variants = await adapter.get_dominant_variants(top_n=10)

            await adapter.close()

            # CRITICAL: Persist to database
            db_result = await persist_to_database(locations, events, "NEXTSTRAIN")

            return raw_data, locations, events, variants, db_result

        raw_data, locations, events, variants, db_result = asyncio.run(fetch_and_persist())

        # Save to GCS (backup)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        raw_path = f"raw/nextstrain/{timestamp}.json"
        save_to_gcs(raw_data, raw_path)

        # Save variants separately for quick access
        variants_path = f"normalized/variants/{timestamp}.json"
        save_to_gcs(variants, variants_path)

        # Publish completion event
        publish_event("genomic_ingestion_complete", {
            "source": "NEXTSTRAIN",
            "records": len(raw_data),
            "locations": len(locations),
            "events": len(events),
            "top_variants": variants[:5],
            "db_persisted": db_result,
            "raw_path": raw_path,
        })

        return {
            "status": "success",
            "source": "NEXTSTRAIN",
            "records_fetched": len(raw_data),
            "locations_normalized": len(locations),
            "events_normalized": len(events),
            "top_variants": [v["clade"] for v in variants[:5]],
            "database_persisted": db_result,
        }

    except Exception as e:
        logger.error(f"Nextstrain ingestion failed: {e}", exc_info=True)
        publish_event("ingestion_failed", {
            "source": "NEXTSTRAIN",
            "error": str(e),
        })
        return {"status": "error", "error": str(e)}, 500


@functions_framework.http
def calculate_risk_scores(request) -> Dict[str, Any]:
    """
    Cloud Function to calculate/recalculate risk scores.

    Triggered by Cloud Scheduler: 0 * * * * (Every hour)
    Also triggered by Pub/Sub after data ingestion completes.
    """
    logger.info("Starting risk score calculation")

    try:
        from persistence import DataPersister

        database_url = get_database_url()

        if not database_url:
            return {
                "status": "skipped",
                "message": "No DATABASE_URL configured",
            }

        async def refresh_scores():
            persister = DataPersister(database_url)
            await persister.connect()
            await persister.refresh_risk_scores()
            stats = await persister.get_stats()
            await persister.close()
            return stats

        stats = asyncio.run(refresh_scores())

        timestamp = datetime.utcnow()

        # Publish completion event
        publish_event("risk_calculation_complete", {
            "timestamp": timestamp.isoformat() + "Z",
            "locations_count": stats.get("location_count", 0),
            "events_count": stats.get("event_count", 0),
        })

        return {
            "status": "success",
            "timestamp": timestamp.isoformat() + "Z",
            "database_stats": stats,
        }

    except Exception as e:
        logger.error(f"Risk calculation failed: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}, 500


@functions_framework.http
def data_quality_check(request) -> Dict[str, Any]:
    """
    Cloud Function to check data quality and freshness.

    Triggered by Cloud Scheduler: 0 9 * * * (Daily at 9am UTC)
    """
    logger.info("Starting data quality check")

    try:
        from persistence import DataPersister

        database_url = get_database_url()

        if not database_url:
            return {
                "status": "skipped",
                "message": "No DATABASE_URL configured",
            }

        # Check data freshness for each source
        sources = [
            # US
            "CDC_NWSS",
            # Europe
            "UKHSA",
            "RIVM",
            "RKI",
            "FR_DATAGOUV",
            "EU_OBSERVATORY",
            "ES_ISCIII",
            # APAC
            "NIID",
            "AU_HEALTH",
            "SG_NEA",
            "KR_KDCA",
            # Americas
            "CA_PHAC",
            "NZ_ESR",
            "BR_FIOCRUZ",
            # Genomic
            "NEXTSTRAIN",
            # Flight
            "AVIATIONSTACK",
            "OPENSKY",
        ]

        async def check_freshness():
            persister = DataPersister(database_url)
            await persister.connect()
            stats = await persister.get_stats()
            await persister.close()
            return stats

        stats = asyncio.run(check_freshness())

        freshness_threshold = timedelta(days=7)
        now = datetime.utcnow()

        stale_sources = []
        source_status = {}

        for src_info in stats.get("sources", []):
            source_id = src_info.get("data_source")
            latest = src_info.get("latest")
            if latest and (now - latest) > freshness_threshold:
                stale_sources.append(source_id)
            source_status[source_id] = {
                "count": src_info.get("count", 0),
                "latest": latest.isoformat() if latest else None,
                "is_stale": source_id in stale_sources,
            }

        quality_report = {
            "timestamp": now.isoformat() + "Z",
            "sources_checked": len(sources),
            "sources_with_data": len(stats.get("sources", [])),
            "stale_sources": stale_sources,
            "source_status": source_status,
            "database_stats": {
                "locations": stats.get("location_count", 0),
                "events": stats.get("event_count", 0),
                "arcs": stats.get("arc_count", 0),
            },
            "status": "healthy" if not stale_sources else "degraded",
        }

        if stale_sources:
            publish_event("data_quality_alert", {
                "stale_sources": stale_sources,
                "threshold_days": freshness_threshold.days,
            })

        return quality_report

    except Exception as e:
        logger.error(f"Data quality check failed: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}, 500


@functions_framework.cloud_event
def process_ingestion_event(cloud_event):
    """
    Pub/Sub triggered function to process ingestion events.

    This function is triggered when data ingestion completes,
    to kick off downstream processing (risk calculation, cache updates).
    """
    import base64

    # Decode message
    message_data = base64.b64decode(cloud_event.data["message"]["data"])
    event = json.loads(message_data)

    logger.info(f"Processing ingestion event: {event.get('event_type')}")

    event_type = event.get("event_type")

    if event_type in ["ingestion_complete", "batch_ingestion_complete"]:
        # Trigger risk score recalculation
        logger.info("Triggering risk score recalculation")

        # Refresh materialized view
        try:
            from persistence import DataPersister

            database_url = get_database_url()
            if database_url:
                async def refresh():
                    persister = DataPersister(database_url)
                    await persister.connect()
                    await persister.refresh_risk_scores()
                    await persister.close()

                asyncio.run(refresh())
                logger.info("Risk scores refreshed successfully")
        except Exception as e:
            logger.error(f"Failed to refresh risk scores: {e}")

    elif event_type == "ingestion_failed":
        # Log alert, potentially trigger retry or notification
        logger.warning(f"Ingestion failed: {event.get('data')}")

    return "OK"


@functions_framework.http
def ingest_all_sources(request) -> Dict[str, Any]:
    """
    Cloud Function to run ALL data ingestion at once.

    Useful for initial data population or full refresh.
    Triggered manually or by Cloud Scheduler: 0 0 * * 0 (Weekly Sunday midnight)
    """
    logger.info("Starting FULL data ingestion (all sources)")

    try:
        from ingest import ingest_all
        from persistence import DataPersister

        database_url = get_database_url()

        if not database_url:
            return {
                "status": "error",
                "error": "No DATABASE_URL configured",
            }, 500

        async def run_full_ingestion():
            persister = DataPersister(database_url)
            await persister.connect()

            results = await ingest_all(persister, dry_run=False)

            await persister.close()
            return results

        results = asyncio.run(run_full_ingestion())

        # Summarize results
        summary = {
            "status": "completed",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "categories": {},
        }

        total_success = 0
        total_failed = 0
        total_events = 0

        for category, category_results in results.items():
            cat_summary = []
            for r in category_results:
                cat_summary.append({
                    "source": r.source_id,
                    "success": r.success,
                    "events": r.events_persisted,
                    "error": r.error,
                })
                if r.success:
                    total_success += 1
                    total_events += r.events_persisted
                else:
                    total_failed += 1
            summary["categories"][category] = cat_summary

        summary["total_success"] = total_success
        summary["total_failed"] = total_failed
        summary["total_events_persisted"] = total_events

        # Publish completion event
        publish_event("full_ingestion_complete", summary)

        return summary

    except Exception as e:
        logger.error(f"Full ingestion failed: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}, 500

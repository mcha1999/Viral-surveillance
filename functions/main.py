"""
Google Cloud Functions for Viral Weather data ingestion.

These functions are triggered by Cloud Scheduler to periodically
fetch and process data from various sources.
"""

import os
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


def publish_event(event_type: str, data: Dict[str, Any]) -> None:
    """Publish event to Pub/Sub for downstream processing."""
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(PROJECT_ID, PUBSUB_TOPIC)

    message = {
        "event_type": event_type,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "data": data,
    }

    publisher.publish(topic_path, json.dumps(message).encode("utf-8"))
    logger.info(f"Published {event_type} event to Pub/Sub")


def save_to_gcs(data: Any, path: str) -> str:
    """Save data to Google Cloud Storage."""
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(path)

    if isinstance(data, (dict, list)):
        blob.upload_from_string(json.dumps(data), content_type="application/json")
    else:
        blob.upload_from_string(str(data))

    logger.info(f"Saved data to gs://{BUCKET_NAME}/{path}")
    return f"gs://{BUCKET_NAME}/{path}"


@functions_framework.http
def ingest_cdc_nwss(request) -> Dict[str, Any]:
    """
    Cloud Function to ingest CDC NWSS wastewater data.

    Triggered by Cloud Scheduler: 0 6 * * 2,4 (Tue/Thu 6am UTC)
    """
    logger.info("Starting CDC NWSS ingestion")

    try:
        # Import adapter (lazy import for cold start optimization)
        import sys
        sys.path.insert(0, '/workspace/data-ingestion')
        from adapters.cdc_nwss import CDCNWSSAdapter

        # Run async adapter
        async def fetch_data():
            adapter = CDCNWSSAdapter()
            raw_data = await adapter.fetch()
            locations, events = adapter.normalize(raw_data)
            await adapter.close()
            return raw_data, locations, events

        raw_data, locations, events = asyncio.run(fetch_data())

        # Save raw data to GCS
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        raw_path = f"raw/cdc_nwss/{timestamp}.json"
        save_to_gcs(raw_data, raw_path)

        # Save normalized data
        locations_path = f"normalized/locations/cdc_nwss_{timestamp}.json"
        events_path = f"normalized/events/cdc_nwss_{timestamp}.json"
        save_to_gcs([loc.__dict__ for loc in locations], locations_path)
        save_to_gcs([evt.__dict__ for evt in events], events_path)

        # Publish completion event
        publish_event("ingestion_complete", {
            "source": "CDC_NWSS",
            "records": len(raw_data),
            "locations": len(locations),
            "events": len(events),
            "raw_path": raw_path,
        })

        return {
            "status": "success",
            "source": "CDC_NWSS",
            "records_fetched": len(raw_data),
            "locations_normalized": len(locations),
            "events_normalized": len(events),
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

    results = []
    errors = []

    # Import adapters
    import sys
    sys.path.insert(0, '/workspace/data-ingestion')

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

                # Save to GCS
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                raw_path = f"raw/{name.lower()}/{timestamp}.json"
                save_to_gcs(raw_data, raw_path)

                all_results.append({
                    "source": name,
                    "status": "success",
                    "records": len(raw_data),
                    "locations": len(locations),
                    "events": len(events),
                })
                logger.info(f"{name}: fetched {len(raw_data)} records")

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
    import sys
    sys.path.insert(0, '/workspace/data-ingestion')

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

                # Save to GCS
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                raw_path = f"raw/{name.lower()}/{timestamp}.json"
                save_to_gcs(raw_data, raw_path)

                all_results.append({
                    "source": name,
                    "status": "success",
                    "records": len(raw_data),
                    "locations": len(locations),
                    "events": len(events),
                })
                logger.info(f"{name}: fetched {len(raw_data)} records")

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
    Cloud Function to ingest flight data from AviationStack.

    Triggered by Cloud Scheduler: 0 */6 * * * (Every 6 hours)
    """
    logger.info("Starting flight data ingestion")

    try:
        # Import adapter
        import sys
        sys.path.insert(0, '/workspace/data-ingestion')
        from adapters.aviationstack import AviationStackAdapter

        # Get API key from Secret Manager
        try:
            api_key = get_secret("aviationstack-api-key")
        except Exception:
            api_key = os.getenv("AVIATIONSTACK_API_KEY")

        async def fetch_routes():
            adapter = AviationStackAdapter(api_key=api_key)
            routes = await adapter.fetch_top_routes()
            await adapter.close()
            return routes

        routes = asyncio.run(fetch_routes())

        # Save to GCS
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        routes_path = f"raw/flights/{timestamp}.json"
        save_to_gcs([r.__dict__ for r in routes], routes_path)

        # Publish completion event
        publish_event("flight_ingestion_complete", {
            "routes": len(routes),
            "path": routes_path,
        })

        return {
            "status": "success",
            "routes_fetched": len(routes),
        }

    except Exception as e:
        logger.error(f"Flight data ingestion failed: {e}", exc_info=True)
        publish_event("ingestion_failed", {
            "source": "AviationStack",
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
        import sys
        sys.path.insert(0, '/workspace/data-ingestion')
        from adapters.nextstrain import NextstrainAdapter

        async def fetch_data():
            adapter = NextstrainAdapter()
            raw_data = await adapter.fetch()
            locations, events = adapter.normalize(raw_data)

            # Get dominant variants
            variants = await adapter.get_dominant_variants(top_n=10)

            await adapter.close()
            return raw_data, locations, events, variants

        raw_data, locations, events, variants = asyncio.run(fetch_data())

        # Save to GCS
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
            "raw_path": raw_path,
        })

        return {
            "status": "success",
            "source": "NEXTSTRAIN",
            "records_fetched": len(raw_data),
            "locations_normalized": len(locations),
            "events_normalized": len(events),
            "top_variants": [v["clade"] for v in variants[:5]],
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
        # In production, this would:
        # 1. Load latest normalized data from Cloud SQL
        # 2. Run risk calculation algorithm
        # 3. Update risk_scores materialized view
        # 4. Update Redis cache

        # For now, return placeholder
        timestamp = datetime.utcnow()

        # Publish completion event
        publish_event("risk_calculation_complete", {
            "timestamp": timestamp.isoformat() + "Z",
            "locations_updated": 0,  # Would be actual count
        })

        return {
            "status": "success",
            "timestamp": timestamp.isoformat() + "Z",
            "message": "Risk score calculation triggered",
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
        ]

        # In production, query database for latest timestamp per source
        # and check against expected freshness thresholds

        stale_sources = []
        freshness_threshold = timedelta(days=7)
        now = datetime.utcnow()

        # Placeholder logic
        quality_report = {
            "timestamp": now.isoformat() + "Z",
            "sources_checked": len(sources),
            "stale_sources": stale_sources,
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
        # In production, this would call calculate_risk_scores or
        # use Cloud Tasks for async processing

    elif event_type == "ingestion_failed":
        # Log alert, potentially trigger retry or notification
        logger.warning(f"Ingestion failed: {event.get('data')}")

    return "OK"

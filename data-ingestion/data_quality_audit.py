#!/usr/bin/env python3
"""
Comprehensive Data Quality Audit System

This script performs a thorough audit of all data sources, checking:
1. Connectivity - Can we connect to the data source?
2. Data Quality - Are values within expected ranges?
3. Data Recency - How fresh is the data?
4. Update Frequency - Is data being updated as expected?
5. Coverage - Are all expected locations present?
6. Completeness - Are there missing fields or values?

Usage:
    python data_quality_audit.py                    # Full audit
    python data_quality_audit.py --quick            # Quick connectivity check
    python data_quality_audit.py --source CDC_NWSS  # Audit specific source
    python data_quality_audit.py --output report.json  # Save report to file
"""

import os
import sys
import asyncio
import argparse
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
import statistics

# Add adapters to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from adapters import (
    WASTEWATER_ADAPTERS,
    GENOMIC_ADAPTERS,
    FLIGHT_ADAPTERS,
    LocationData,
    SurveillanceEvent,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class AuditStatus(Enum):
    """Audit status levels."""
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"
    SKIP = "SKIP"


@dataclass
class DataQualityMetrics:
    """Metrics for data quality assessment."""
    total_records: int = 0
    null_values: int = 0
    out_of_range_values: int = 0
    duplicate_records: int = 0
    completeness_score: float = 0.0  # 0-1
    validity_score: float = 0.0  # 0-1
    consistency_score: float = 0.0  # 0-1


@dataclass
class RecencyMetrics:
    """Metrics for data recency assessment."""
    oldest_record: Optional[datetime] = None
    newest_record: Optional[datetime] = None
    age_days: float = 0.0
    expected_frequency_days: float = 7.0  # Expected update frequency
    is_stale: bool = False
    staleness_threshold_days: float = 14.0


@dataclass
class CoverageMetrics:
    """Metrics for data coverage assessment."""
    expected_locations: int = 0
    actual_locations: int = 0
    coverage_percentage: float = 0.0
    missing_locations: List[str] = field(default_factory=list)


@dataclass
class SourceAuditResult:
    """Comprehensive audit result for a single data source."""
    source_id: str
    source_name: str
    timestamp: datetime
    status: AuditStatus

    # Connectivity
    connectivity_status: AuditStatus = AuditStatus.SKIP
    connectivity_message: str = ""
    fetch_duration_seconds: float = 0.0

    # Raw data stats
    records_fetched: int = 0
    locations_normalized: int = 0
    events_normalized: int = 0

    # Quality metrics
    quality_metrics: Optional[DataQualityMetrics] = None
    quality_status: AuditStatus = AuditStatus.SKIP

    # Recency metrics
    recency_metrics: Optional[RecencyMetrics] = None
    recency_status: AuditStatus = AuditStatus.SKIP

    # Coverage metrics
    coverage_metrics: Optional[CoverageMetrics] = None
    coverage_status: AuditStatus = AuditStatus.SKIP

    # Additional info
    is_proxy_data: bool = False
    api_key_required: bool = False
    api_key_present: bool = False
    error_message: Optional[str] = None
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "source_id": self.source_id,
            "source_name": self.source_name,
            "timestamp": self.timestamp.isoformat(),
            "status": self.status.value,
            "connectivity_status": self.connectivity_status.value,
            "connectivity_message": self.connectivity_message,
            "fetch_duration_seconds": round(self.fetch_duration_seconds, 2),
            "records_fetched": self.records_fetched,
            "locations_normalized": self.locations_normalized,
            "events_normalized": self.events_normalized,
            "quality_status": self.quality_status.value,
            "recency_status": self.recency_status.value,
            "coverage_status": self.coverage_status.value,
            "is_proxy_data": self.is_proxy_data,
            "api_key_required": self.api_key_required,
            "api_key_present": self.api_key_present,
            "error_message": self.error_message,
            "warnings": self.warnings,
        }

        if self.quality_metrics:
            result["quality_metrics"] = asdict(self.quality_metrics)
        if self.recency_metrics:
            rm = self.recency_metrics
            result["recency_metrics"] = {
                "oldest_record": rm.oldest_record.isoformat() if rm.oldest_record else None,
                "newest_record": rm.newest_record.isoformat() if rm.newest_record else None,
                "age_days": round(rm.age_days, 1),
                "expected_frequency_days": rm.expected_frequency_days,
                "is_stale": rm.is_stale,
            }
        if self.coverage_metrics:
            result["coverage_metrics"] = asdict(self.coverage_metrics)

        return result


# Expected update frequencies for each source (in days)
EXPECTED_FREQUENCIES = {
    "CDC_NWSS": 3,
    "UKHSA": 7,
    "RIVM": 7,
    "RKI": 7,
    "FR_DATAGOUV": 7,
    "NIID": 7,
    "AU_HEALTH": 7,
    "EU_OBSERVATORY": 7,
    "ES_ISCIII": 7,
    "CA_PHAC": 7,
    "NZ_ESR": 7,
    "SG_NEA": 7,
    "KR_KDCA": 7,
    "BR_FIOCRUZ": 7,
    "NEXTSTRAIN": 1,  # Daily updates
    "AVIATIONSTACK": 0.25,  # 6-hour updates
}

# Expected location counts per source
EXPECTED_LOCATIONS = {
    "CDC_NWSS": 50,  # ~50 US states/territories
    "UKHSA": 13,  # UK regions
    "RIVM": 12,  # Dutch provinces
    "RKI": 16,  # German states
    "FR_DATAGOUV": 13,  # French regions
    "NIID": 47,  # Japanese prefectures
    "AU_HEALTH": 8,  # Australian states/territories
    "EU_OBSERVATORY": 20,  # EU countries
    "ES_ISCIII": 17,  # Spanish communities
    "CA_PHAC": 13,  # Canadian provinces
    "NZ_ESR": 5,  # NZ regions
    "SG_NEA": 1,  # Singapore national
    "KR_KDCA": 17,  # Korean provinces
    "BR_FIOCRUZ": 27,  # Brazilian states
    "NEXTSTRAIN": 19,  # Tracked countries
    "AVIATIONSTACK": 40,  # Major airports
}

# API keys required for sources
API_KEY_ENV_VARS = {
    "AVIATIONSTACK": "AVIATIONSTACK_API_KEY",
    "KR_KDCA": "KOREA_OPENDATA_API_KEY",
    "BR_FIOCRUZ": "BRASIL_IO_TOKEN",
}


class DataQualityAuditor:
    """Comprehensive data quality auditor."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.results: List[SourceAuditResult] = []

    async def audit_source(
        self,
        source_id: str,
        adapter_class: type,
        category: str = "wastewater"
    ) -> SourceAuditResult:
        """Perform comprehensive audit of a single data source."""
        logger.info(f"Auditing {source_id}...")

        result = SourceAuditResult(
            source_id=source_id,
            source_name=adapter_class.__name__,
            timestamp=datetime.utcnow(),
            status=AuditStatus.SKIP,
        )

        # Check API key requirements
        if source_id in API_KEY_ENV_VARS:
            result.api_key_required = True
            env_var = API_KEY_ENV_VARS[source_id]
            result.api_key_present = bool(os.getenv(env_var))
            if not result.api_key_present:
                result.warnings.append(f"API key not set: {env_var}")

        # Test connectivity and fetch data
        start_time = datetime.utcnow()
        try:
            adapter = adapter_class()
            raw_data = await adapter.fetch()
            result.fetch_duration_seconds = (datetime.utcnow() - start_time).total_seconds()

            if raw_data:
                result.records_fetched = len(raw_data)
                result.connectivity_status = AuditStatus.PASS
                result.connectivity_message = f"Fetched {len(raw_data)} records"

                # Normalize data
                locations, events = adapter.normalize(raw_data)
                result.locations_normalized = len(locations)
                result.events_normalized = len(events)

                # Check for proxy data (UK adapter)
                if hasattr(adapter, 'is_using_proxy_data') and adapter.is_using_proxy_data:
                    result.is_proxy_data = True
                    result.warnings.append("Using proxy data (not actual wastewater)")

                # Perform quality checks
                result.quality_metrics = self._assess_quality(raw_data, events)
                result.quality_status = self._grade_quality(result.quality_metrics)

                # Perform recency checks
                result.recency_metrics = self._assess_recency(
                    events,
                    EXPECTED_FREQUENCIES.get(source_id, 7)
                )
                result.recency_status = self._grade_recency(result.recency_metrics)

                # Perform coverage checks
                result.coverage_metrics = self._assess_coverage(
                    locations,
                    EXPECTED_LOCATIONS.get(source_id, 10)
                )
                result.coverage_status = self._grade_coverage(result.coverage_metrics)

            else:
                result.connectivity_status = AuditStatus.WARN
                result.connectivity_message = "No data returned"
                result.warnings.append("API returned empty data")

            await adapter.close()

        except Exception as e:
            result.fetch_duration_seconds = (datetime.utcnow() - start_time).total_seconds()
            result.connectivity_status = AuditStatus.FAIL
            result.connectivity_message = str(e)
            result.error_message = str(e)
            logger.error(f"[{source_id}] Audit failed: {e}")

        # Calculate overall status
        result.status = self._calculate_overall_status(result)

        return result

    def _assess_quality(
        self,
        raw_data: List[Dict[str, Any]],
        events: List[SurveillanceEvent]
    ) -> DataQualityMetrics:
        """Assess data quality metrics."""
        metrics = DataQualityMetrics(total_records=len(raw_data))

        if not events:
            return metrics

        # Check for null/missing values
        null_count = 0
        out_of_range = 0

        for event in events:
            if event.normalized_score is None:
                null_count += 1
            elif not (0 <= event.normalized_score <= 1):
                out_of_range += 1

        metrics.null_values = null_count
        metrics.out_of_range_values = out_of_range

        # Calculate completeness (percentage of non-null values)
        if events:
            non_null = len(events) - null_count
            metrics.completeness_score = non_null / len(events)

        # Calculate validity (percentage of in-range values)
        non_null_events = len(events) - null_count
        if non_null_events > 0:
            metrics.validity_score = (non_null_events - out_of_range) / non_null_events

        # Check for duplicates (simplified check on event IDs)
        event_ids = [e.event_id for e in events]
        unique_ids = set(event_ids)
        metrics.duplicate_records = len(event_ids) - len(unique_ids)

        # Consistency score based on no duplicates and valid data
        if metrics.duplicate_records == 0:
            metrics.consistency_score = 1.0
        else:
            metrics.consistency_score = max(0, 1 - (metrics.duplicate_records / len(events)))

        return metrics

    def _assess_recency(
        self,
        events: List[SurveillanceEvent],
        expected_frequency_days: float
    ) -> RecencyMetrics:
        """Assess data recency metrics."""
        metrics = RecencyMetrics(expected_frequency_days=expected_frequency_days)

        if not events:
            metrics.is_stale = True
            return metrics

        # Get date range
        timestamps = [e.timestamp for e in events if e.timestamp]
        if timestamps:
            metrics.oldest_record = min(timestamps)
            metrics.newest_record = max(timestamps)

            # Calculate age in days
            now = datetime.utcnow()
            age = now - metrics.newest_record
            metrics.age_days = age.total_seconds() / 86400

            # Check if stale (more than 2x expected frequency)
            metrics.staleness_threshold_days = expected_frequency_days * 2
            metrics.is_stale = metrics.age_days > metrics.staleness_threshold_days

        return metrics

    def _assess_coverage(
        self,
        locations: List[LocationData],
        expected_locations: int
    ) -> CoverageMetrics:
        """Assess data coverage metrics."""
        metrics = CoverageMetrics(
            expected_locations=expected_locations,
            actual_locations=len(locations),
        )

        if expected_locations > 0:
            metrics.coverage_percentage = min(100, (len(locations) / expected_locations) * 100)

        return metrics

    def _grade_quality(self, metrics: DataQualityMetrics) -> AuditStatus:
        """Grade quality metrics."""
        if not metrics or metrics.total_records == 0:
            return AuditStatus.FAIL

        avg_score = (
            metrics.completeness_score +
            metrics.validity_score +
            metrics.consistency_score
        ) / 3

        if avg_score >= 0.9:
            return AuditStatus.PASS
        elif avg_score >= 0.7:
            return AuditStatus.WARN
        else:
            return AuditStatus.FAIL

    def _grade_recency(self, metrics: RecencyMetrics) -> AuditStatus:
        """Grade recency metrics."""
        if not metrics or metrics.newest_record is None:
            return AuditStatus.FAIL

        if metrics.is_stale:
            return AuditStatus.FAIL
        elif metrics.age_days > metrics.expected_frequency_days:
            return AuditStatus.WARN
        else:
            return AuditStatus.PASS

    def _grade_coverage(self, metrics: CoverageMetrics) -> AuditStatus:
        """Grade coverage metrics."""
        if not metrics:
            return AuditStatus.SKIP

        if metrics.coverage_percentage >= 80:
            return AuditStatus.PASS
        elif metrics.coverage_percentage >= 50:
            return AuditStatus.WARN
        else:
            return AuditStatus.FAIL

    def _calculate_overall_status(self, result: SourceAuditResult) -> AuditStatus:
        """Calculate overall audit status."""
        if result.connectivity_status == AuditStatus.FAIL:
            return AuditStatus.FAIL

        if result.error_message:
            return AuditStatus.FAIL

        statuses = [
            result.connectivity_status,
            result.quality_status,
            result.recency_status,
            result.coverage_status,
        ]

        # Filter out SKIP statuses
        active_statuses = [s for s in statuses if s != AuditStatus.SKIP]

        if not active_statuses:
            return AuditStatus.SKIP

        if any(s == AuditStatus.FAIL for s in active_statuses):
            return AuditStatus.FAIL
        elif any(s == AuditStatus.WARN for s in active_statuses):
            return AuditStatus.WARN
        else:
            return AuditStatus.PASS

    async def run_full_audit(self) -> Dict[str, Any]:
        """Run full audit across all data sources."""
        logger.info("Starting full data quality audit...")
        start_time = datetime.utcnow()

        results = {
            "wastewater": [],
            "genomic": [],
            "flight": [],
        }

        # Audit wastewater sources
        for source_id, adapter_class in WASTEWATER_ADAPTERS.items():
            result = await self.audit_source(source_id, adapter_class, "wastewater")
            results["wastewater"].append(result)
            self.results.append(result)

        # Audit genomic sources
        for source_id, adapter_class in GENOMIC_ADAPTERS.items():
            result = await self.audit_source(source_id, adapter_class, "genomic")
            results["genomic"].append(result)
            self.results.append(result)

        # Audit flight sources
        for source_id, adapter_class in FLIGHT_ADAPTERS.items():
            result = await self.audit_source(source_id, adapter_class, "flight")
            results["flight"].append(result)
            self.results.append(result)

        duration = (datetime.utcnow() - start_time).total_seconds()

        return self._generate_report(results, duration)

    async def run_quick_audit(self) -> Dict[str, Any]:
        """Run quick connectivity check only."""
        logger.info("Running quick connectivity audit...")
        start_time = datetime.utcnow()

        results = []
        all_adapters = {**WASTEWATER_ADAPTERS, **GENOMIC_ADAPTERS, **FLIGHT_ADAPTERS}

        for source_id, adapter_class in all_adapters.items():
            logger.info(f"Testing {source_id}...")
            try:
                adapter = adapter_class()
                fetch_start = datetime.utcnow()
                raw_data = await adapter.fetch()
                fetch_duration = (datetime.utcnow() - fetch_start).total_seconds()
                await adapter.close()

                results.append({
                    "source_id": source_id,
                    "status": "PASS" if raw_data else "WARN",
                    "records": len(raw_data) if raw_data else 0,
                    "duration_seconds": round(fetch_duration, 2),
                })
            except Exception as e:
                results.append({
                    "source_id": source_id,
                    "status": "FAIL",
                    "error": str(e),
                    "duration_seconds": 0,
                })

        duration = (datetime.utcnow() - start_time).total_seconds()

        passed = sum(1 for r in results if r["status"] == "PASS")
        warned = sum(1 for r in results if r["status"] == "WARN")
        failed = sum(1 for r in results if r["status"] == "FAIL")

        return {
            "type": "quick_audit",
            "timestamp": datetime.utcnow().isoformat(),
            "duration_seconds": round(duration, 2),
            "summary": {
                "total": len(results),
                "passed": passed,
                "warned": warned,
                "failed": failed,
            },
            "results": results,
        }

    def _generate_report(
        self,
        results: Dict[str, List[SourceAuditResult]],
        duration: float
    ) -> Dict[str, Any]:
        """Generate comprehensive audit report."""
        all_results = []
        for category_results in results.values():
            all_results.extend(category_results)

        # Calculate summary statistics
        total = len(all_results)
        passed = sum(1 for r in all_results if r.status == AuditStatus.PASS)
        warned = sum(1 for r in all_results if r.status == AuditStatus.WARN)
        failed = sum(1 for r in all_results if r.status == AuditStatus.FAIL)
        skipped = sum(1 for r in all_results if r.status == AuditStatus.SKIP)

        # Calculate average metrics
        total_records = sum(r.records_fetched for r in all_results)
        total_locations = sum(r.locations_normalized for r in all_results)
        total_events = sum(r.events_normalized for r in all_results)

        # Get stale sources
        stale_sources = [
            r.source_id for r in all_results
            if r.recency_metrics and r.recency_metrics.is_stale
        ]

        # Get proxy data sources
        proxy_sources = [r.source_id for r in all_results if r.is_proxy_data]

        # Get sources missing API keys
        missing_keys = [
            r.source_id for r in all_results
            if r.api_key_required and not r.api_key_present
        ]

        report = {
            "type": "full_audit",
            "timestamp": datetime.utcnow().isoformat(),
            "duration_seconds": round(duration, 2),
            "summary": {
                "total_sources": total,
                "passed": passed,
                "warned": warned,
                "failed": failed,
                "skipped": skipped,
                "health_score": round((passed / total) * 100, 1) if total > 0 else 0,
            },
            "data_summary": {
                "total_records_fetched": total_records,
                "total_locations": total_locations,
                "total_events": total_events,
            },
            "issues": {
                "stale_sources": stale_sources,
                "proxy_data_sources": proxy_sources,
                "missing_api_keys": missing_keys,
            },
            "results": {
                category: [r.to_dict() for r in category_results]
                for category, category_results in results.items()
            },
        }

        return report


def print_report(report: Dict[str, Any]) -> None:
    """Print a human-readable audit report."""
    print("\n" + "=" * 70)
    print(" DATA QUALITY AUDIT REPORT")
    print("=" * 70)

    summary = report["summary"]
    print(f"\nTimestamp: {report['timestamp']}")
    print(f"Duration: {report['duration_seconds']}s")
    print(f"\nHealth Score: {summary.get('health_score', 'N/A')}%")
    print(f"  Total Sources: {summary['total_sources'] if 'total_sources' in summary else summary.get('total', 'N/A')}")
    print(f"  ✓ Passed: {summary['passed']}")
    print(f"  ⚠ Warned: {summary['warned']}")
    print(f"  ✗ Failed: {summary['failed']}")

    if report["type"] == "full_audit":
        data_summary = report["data_summary"]
        print(f"\nData Summary:")
        print(f"  Records Fetched: {data_summary['total_records_fetched']:,}")
        print(f"  Locations: {data_summary['total_locations']:,}")
        print(f"  Events: {data_summary['total_events']:,}")

        issues = report["issues"]
        if issues["stale_sources"]:
            print(f"\n⚠️  STALE DATA: {', '.join(issues['stale_sources'])}")
        if issues["proxy_data_sources"]:
            print(f"⚠️  PROXY DATA: {', '.join(issues['proxy_data_sources'])}")
        if issues["missing_api_keys"]:
            print(f"⚠️  MISSING API KEYS: {', '.join(issues['missing_api_keys'])}")

        print("\n" + "-" * 70)
        print(" DETAILED RESULTS BY CATEGORY")
        print("-" * 70)

        for category, results_list in report["results"].items():
            print(f"\n{category.upper()}:")
            for result in results_list:
                status_icon = {
                    "PASS": "✓",
                    "WARN": "⚠",
                    "FAIL": "✗",
                    "SKIP": "○",
                }[result["status"]]

                print(f"  {status_icon} {result['source_id']}: "
                      f"{result['records_fetched']} records, "
                      f"{result['locations_normalized']} locations "
                      f"({result['fetch_duration_seconds']}s)")

                if result.get("error_message"):
                    print(f"    └─ Error: {result['error_message'][:50]}...")
                if result.get("warnings"):
                    for warn in result["warnings"]:
                        print(f"    └─ Warning: {warn}")

    else:
        # Quick audit
        print("\n" + "-" * 70)
        print(" CONNECTIVITY RESULTS")
        print("-" * 70)

        for result in report["results"]:
            status_icon = {"PASS": "✓", "WARN": "⚠", "FAIL": "✗"}[result["status"]]
            if result["status"] == "FAIL":
                print(f"  {status_icon} {result['source_id']}: {result.get('error', 'Failed')[:40]}...")
            else:
                print(f"  {status_icon} {result['source_id']}: {result['records']} records ({result['duration_seconds']}s)")

    print("\n" + "=" * 70 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Comprehensive Data Quality Audit System"
    )

    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick connectivity check only"
    )
    parser.add_argument(
        "--source",
        type=str,
        help="Audit a specific source only"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Save report to JSON file"
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

    auditor = DataQualityAuditor(verbose=args.verbose)

    if args.source:
        # Audit specific source
        all_adapters = {**WASTEWATER_ADAPTERS, **GENOMIC_ADAPTERS, **FLIGHT_ADAPTERS}
        if args.source not in all_adapters:
            print(f"Unknown source: {args.source}")
            print(f"Available sources: {', '.join(all_adapters.keys())}")
            return

        result = asyncio.run(
            auditor.audit_source(args.source, all_adapters[args.source])
        )
        report = {
            "type": "single_source_audit",
            "timestamp": datetime.utcnow().isoformat(),
            "result": result.to_dict(),
        }
        print(json.dumps(report, indent=2))

    elif args.quick:
        report = asyncio.run(auditor.run_quick_audit())
        print_report(report)

    else:
        report = asyncio.run(auditor.run_full_audit())
        print_report(report)

    if args.output:
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2, default=str)
        print(f"Report saved to {args.output}")


if __name__ == "__main__":
    main()

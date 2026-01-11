#!/usr/bin/env python3
"""
Quick test script to verify adapters can fetch real data.
No database required - just tests API connectivity.

Usage:
    python3 test_adapters.py
    python3 test_adapters.py --source nextstrain
    python3 test_adapters.py --source opensky
    python3 test_adapters.py --source cdc
"""

import asyncio
import argparse
import sys
from datetime import datetime


async def test_nextstrain():
    """Test Nextstrain genomic data (FREE, no API key)."""
    print("\n" + "=" * 60)
    print("Testing NEXTSTRAIN (FREE - no API key needed)")
    print("=" * 60)

    try:
        from adapters.nextstrain import NextstrainAdapter

        adapter = NextstrainAdapter()
        print("Fetching Nextstrain clade frequencies...")

        raw_data = await adapter.fetch()
        print(f"  Raw records fetched: {len(raw_data)}")

        locations, events = adapter.normalize(raw_data)
        print(f"  Locations normalized: {len(locations)}")
        print(f"  Events normalized: {len(events)}")

        # Get top variants
        variants = await adapter.get_dominant_variants(top_n=5)
        print(f"\n  Top 5 variants:")
        for v in variants[:5]:
            print(f"    - {v['clade']}: {v['frequency']:.1%}")

        await adapter.close()
        print("\n  STATUS: SUCCESS")
        return True

    except Exception as e:
        print(f"\n  STATUS: FAILED - {e}")
        return False


async def test_opensky():
    """Test OpenSky flight data (FREE, no API key required)."""
    print("\n" + "=" * 60)
    print("Testing OPENSKY (FREE - no API key needed)")
    print("=" * 60)

    try:
        from adapters.opensky import OpenSkyAdapter

        adapter = OpenSkyAdapter()
        print("Fetching flight arrivals from major airports...")
        print("(This may take 30-60 seconds due to rate limiting)")

        # Test with just 3 airports to be quick
        test_airports = ["KJFK", "EGLL", "WSSS"]

        for icao in test_airports:
            print(f"\n  Checking {icao}...")
            arrivals = await adapter.fetch_arrivals(icao)
            print(f"    Arrivals in last 24h: {len(arrivals)}")

            if arrivals:
                # Show top origins
                origins = {}
                for arr in arrivals:
                    if arr.origin_airport:
                        origins[arr.origin_airport] = origins.get(arr.origin_airport, 0) + 1

                top_origins = sorted(origins.items(), key=lambda x: x[1], reverse=True)[:3]
                if top_origins:
                    print(f"    Top origins: {', '.join([f'{o[0]}({o[1]})' for o in top_origins])}")

            await asyncio.sleep(1)  # Rate limiting

        await adapter.close()
        print("\n  STATUS: SUCCESS")
        return True

    except Exception as e:
        print(f"\n  STATUS: FAILED - {e}")
        return False


async def test_cdc_nwss():
    """Test CDC NWSS wastewater data (FREE, no API key)."""
    print("\n" + "=" * 60)
    print("Testing CDC NWSS (FREE - no API key needed)")
    print("=" * 60)

    try:
        from adapters.cdc_nwss import CDCNWSSAdapter

        adapter = CDCNWSSAdapter()
        print("Fetching CDC NWSS wastewater surveillance data...")

        raw_data = await adapter.fetch()
        print(f"  Raw records fetched: {len(raw_data)}")

        if raw_data:
            locations, events = adapter.normalize(raw_data)
            print(f"  Locations normalized: {len(locations)}")
            print(f"  Events normalized: {len(events)}")

            # Show sample data
            if events:
                recent = sorted(events, key=lambda e: e.timestamp, reverse=True)[:3]
                print(f"\n  Recent events:")
                for evt in recent:
                    print(f"    - {evt.location_id}: {evt.value:.2f} ({evt.timestamp.date()})")

        await adapter.close()
        print("\n  STATUS: SUCCESS")
        return True

    except Exception as e:
        print(f"\n  STATUS: FAILED - {e}")
        return False


async def test_european():
    """Test European wastewater sources."""
    print("\n" + "=" * 60)
    print("Testing EUROPEAN SOURCES")
    print("=" * 60)

    from adapters import (
        NLRIVMAdapter,
        EUWastewaterObservatoryAdapter,
    )

    results = {}

    # Test RIVM (Netherlands)
    try:
        print("\n  Testing NL RIVM...")
        adapter = NLRIVMAdapter()
        data = await adapter.fetch()
        await adapter.close()
        print(f"    Records: {len(data)}")
        results["RIVM"] = len(data) > 0
    except Exception as e:
        print(f"    Error: {e}")
        results["RIVM"] = False

    # Test EU Observatory
    try:
        print("\n  Testing EU Observatory...")
        adapter = EUWastewaterObservatoryAdapter()
        data = await adapter.fetch()
        await adapter.close()
        print(f"    Records: {len(data)}")
        results["EU_OBS"] = len(data) > 0
    except Exception as e:
        print(f"    Error: {e}")
        results["EU_OBS"] = False

    success = all(results.values())
    print(f"\n  STATUS: {'SUCCESS' if success else 'PARTIAL'}")
    return success


async def run_all_tests():
    """Run all adapter tests."""
    print("\n" + "#" * 60)
    print("# VIRAL SURVEILLANCE - ADAPTER CONNECTIVITY TEST")
    print(f"# Time: {datetime.now().isoformat()}")
    print("#" * 60)

    results = {}

    # Test free APIs that don't require keys
    results["nextstrain"] = await test_nextstrain()
    results["opensky"] = await test_opensky()
    results["cdc_nwss"] = await test_cdc_nwss()

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    for source, success in results.items():
        status = "PASS" if success else "FAIL"
        print(f"  {source.upper():20} {status}")

    total_pass = sum(results.values())
    total = len(results)
    print(f"\n  Total: {total_pass}/{total} passed")

    if total_pass == total:
        print("\n  All adapters working! Ready for production.")
    else:
        print("\n  Some adapters failed. Check errors above.")

    return all(results.values())


async def main():
    parser = argparse.ArgumentParser(description="Test data adapters")
    parser.add_argument(
        "--source",
        choices=["nextstrain", "opensky", "cdc", "european", "all"],
        default="all",
        help="Which source to test"
    )
    args = parser.parse_args()

    if args.source == "nextstrain":
        await test_nextstrain()
    elif args.source == "opensky":
        await test_opensky()
    elif args.source == "cdc":
        await test_cdc_nwss()
    elif args.source == "european":
        await test_european()
    else:
        await run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python
"""
Quick seed data generator - uses fastest available method
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from seeds.seed_data_generator_fast import FastBulkSeedGenerator

async def main():
    """Run fast seed generation"""
    print("=" * 60)
    print("QUICK SEED DATA GENERATOR")
    print("=" * 60)
    
    generator = FastBulkSeedGenerator()
    try:
        await generator.generate_all()
        print("\n" + "=" * 60)
        print("OK: SEED DATA GENERATION COMPLETE!")
        print("=" * 60)
        print("\nDatabase now contains:")
        print("  * 10,000 accounts (7000 normal, 300 fraud, 2700 suspicious)")
        print("  * Shared devices, IPs, and phone numbers")
        print("  * Money-mule chains with known-fraud anchors")
        print("  * Fraud ring detection patterns")
        print("\nYou can now use the application at http://localhost:5173")
    except Exception as e:
        print(f"\nERROR: {e}")
        raise
    finally:
        await generator.close()

if __name__ == "__main__":
    asyncio.run(main())

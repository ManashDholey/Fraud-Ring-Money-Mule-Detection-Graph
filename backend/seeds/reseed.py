"""
Trigger enhanced fraud pattern seeding.
"""
import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

from seeds.seed_data_generator_async import SeedDataGenerator


async def main():
    print("\n" + "="*70)
    print("RE-SEEDING DATABASE WITH ENHANCED FRAUD PATTERNS")
    print("="*70)
    
    generator = SeedDataGenerator()
    try:
        await generator.generate_all()
        print("\n✓ Database re-seeded successfully with enhanced patterns!")
        print("✓ Fraud Rings page should now show 5 fraud rings")
        print("✓ Transactions page should now show money-mule chains")
    except Exception as e:
        print(f"\n✗ Seeding failed: {e}")
        raise
    finally:
        await generator.close()


if __name__ == "__main__":
    asyncio.run(main())

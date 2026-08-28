#!/usr/bin/env python3
"""
Call the admin reseed endpoint via HTTP to populate database with fraud data.
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def reseed_database():
    """Call the reseed admin endpoint."""
    print("Calling reseed endpoint...")
    try:
        response = requests.post(f"{BASE_URL}/api/admin/reseed", timeout=30)
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Reseed successful!")
            print(json.dumps(data, indent=2))
            return True
        else:
            print(f"❌ Reseed failed: {response.status_code}")
            print(response.text)
            return False
    except Exception as e:
        print(f"❌ Error calling reseed: {e}")
        return False

def check_fraud_rings():
    """Check if fraud rings are now available."""
    print("\nChecking fraud rings...")
    try:
        response = requests.get(f"{BASE_URL}/api/networks/fraud-rings", timeout=10)
        if response.status_code == 200:
            data = response.json()
            ring_count = len(data.get('items', []))
            print(f"✓ Fraud rings found: {ring_count}")
            if ring_count > 0:
                print(f"  Sample ring: {json.dumps(data['items'][0], indent=2)}")
            return ring_count > 0
        else:
            print(f"❌ API error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error querying fraud rings: {e}")
        return False

def check_dashboard():
    """Check dashboard stats."""
    print("\nChecking dashboard...")
    try:
        response = requests.get(f"{BASE_URL}/api/dashboard", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Dashboard stats:")
            print(f"  Total accounts: {data.get('totalAccounts', 0)}")
            print(f"  Known fraud: {data.get('knownFraudAccounts', 0)}")
            print(f"  Fraud rings: {data.get('detectedFraudRings', 0)}")
            print(f"  Medium risk: {data.get('mediumRiskAccounts', 0)}")
            print(f"  High risk: {data.get('highRiskAccounts', 0)}")
            print(f"  Critical risk: {data.get('criticalRiskAccounts', 0)}")
            return True
        else:
            print(f"❌ API error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error querying dashboard: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("DATABASE POPULATION SCRIPT")
    print("=" * 60 + "\n")
    
    # Step 1: Reseed the database
    if reseed_database():
        print("\n⏳ Waiting for database to settle...\n")
        time.sleep(2)
        
        # Step 2: Check results
        check_dashboard()
        check_fraud_rings()
        print("\n" + "=" * 60)
        print("✅ COMPLETE")
        print("=" * 60)
    else:
        print("\n❌ Failed to reseed database")

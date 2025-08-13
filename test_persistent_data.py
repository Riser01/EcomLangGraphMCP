#!/usr/bin/env python3
"""
Test script to verify the persistent data solution works correctly.
"""

import asyncio
import sys
import os

# Add the current directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from persistent_data import persistent_orders_db

def test_persistent_data():
    """Test the persistent data functionality."""
    print("🧪 Testing Persistent Data Solution...")
    
    # Test 1: Check if ORDZW011 exists
    print("\n1️⃣ Checking if ORDZW011 exists...")
    order = persistent_orders_db.get("ORDZW011")
    if order:
        print(f"✅ Found ORDZW011: Status = '{order['status']}'")
    else:
        print("❌ ORDZW011 not found!")
        return False
    
    # Test 2: Update the order status
    print("\n2️⃣ Updating ORDZW011 to 'Cancelled'...")
    result = persistent_orders_db.update("ORDZW011", {
        "status": "Cancelled",
        "estimated_delivery_time": None
    })
    
    if result:
        print("✅ Update successful")
    else:
        print("❌ Update failed!")
        return False
    
    # Test 3: Verify the update persisted
    print("\n3️⃣ Verifying the update...")
    updated_order = persistent_orders_db.get("ORDZW011")
    if updated_order and updated_order['status'] == 'Cancelled':
        print(f"✅ Status correctly updated to: '{updated_order['status']}'")
    else:
        print(f"❌ Status not updated correctly. Current status: '{updated_order['status'] if updated_order else 'NOT FOUND'}'")
        return False
    
    # Test 4: Check if data persisted to file
    print("\n4️⃣ Checking if data was saved to file...")
    if os.path.exists("orders_db.json"):
        print("✅ orders_db.json file created")
        # Load and check
        import json
        with open("orders_db.json", 'r') as f:
            file_data = json.load(f)
        
        if file_data.get("ORDZW011", {}).get("status") == "Cancelled":
            print("✅ Status persisted to file correctly")
        else:
            print(f"❌ File data incorrect: {file_data.get('ORDZW011', {}).get('status')}")
            return False
    else:
        print("❌ orders_db.json file not created")
        return False
    
    print("\n🎉 All tests passed! Persistent data solution is working correctly.")
    return True

if __name__ == "__main__":
    success = test_persistent_data()
    if not success:
        print("\n💥 Tests failed! Please check the implementation.")
        sys.exit(1)
    else:
        print("\n✅ All tests passed!")

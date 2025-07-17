#!/usr/bin/env python3
"""
Test script to verify reading progress endpoint accepts float values.
This is a simple test to ensure the fixes work correctly.
"""

import json
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from pydantic import ValidationError
from src.routers.constitution_routes import ReadingProgressRequest

def test_reading_progress_request():
    """Test that ReadingProgressRequest accepts float values."""
    
    print("Testing ReadingProgressRequest with float values...")
    
    # Test case 1: Integer value (should work)
    try:
        request1 = ReadingProgressRequest(
            item_type="chapter",
            reference="4",
            read_time_minutes=1
        )
        print("✓ Integer value test passed")
    except ValidationError as e:
        print(f"✗ Integer value test failed: {e}")
        return False
    
    # Test case 2: Float value (should work after our fix)
    try:
        request2 = ReadingProgressRequest(
            item_type="chapter",
            reference="4",
            read_time_minutes=1.59
        )
        print("✓ Float value test passed")
    except ValidationError as e:
        print(f"✗ Float value test failed: {e}")
        return False
    
    # Test case 3: With is_incremental field (should work after our fix)
    try:
        request3 = ReadingProgressRequest(
            item_type="chapter",
            reference="4",
            read_time_minutes=1.59,
            is_incremental=True
        )
        print("✓ is_incremental field test passed")
    except ValidationError as e:
        print(f"✗ is_incremental field test failed: {e}")
        return False
    
    # Test case 4: JSON parsing like from frontend
    try:
        json_data = {
            "item_type": "chapter",
            "reference": "4",
            "read_time_minutes": 1.59,
            "is_incremental": True
        }
        request4 = ReadingProgressRequest(**json_data)
        print("✓ JSON parsing test passed")
    except ValidationError as e:
        print(f"✗ JSON parsing test failed: {e}")
        return False
    
    print("\nAll tests passed! ReadingProgressRequest now accepts float values.")
    return True

if __name__ == "__main__":
    success = test_reading_progress_request()
    sys.exit(0 if success else 1)
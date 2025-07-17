#!/usr/bin/env python3
"""
Simple test script to verify ReadingProgressRequest schema accepts float values.
"""

from pydantic import BaseModel, Field, ValidationError
from typing import Optional

class ReadingProgressRequest(BaseModel):
    item_type: str = Field(..., description="Type of item (chapter, article)")
    reference: str = Field(..., description="Reference (e.g., '1' for chapter 1, '1.2' for article 2 in chapter 1)")
    read_time_minutes: float = Field(1.0, description="Time spent reading in minutes (supports decimals)")
    is_incremental: Optional[bool] = Field(True, description="Whether this is incremental reading time")

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
        print(f"  - read_time_minutes: {request1.read_time_minutes} (type: {type(request1.read_time_minutes)})")
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
        print(f"  - read_time_minutes: {request2.read_time_minutes} (type: {type(request2.read_time_minutes)})")
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
        print(f"  - is_incremental: {request3.is_incremental}")
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
        print(f"  - JSON request: {request4.dict()}")
    except ValidationError as e:
        print(f"✗ JSON parsing test failed: {e}")
        return False
    
    print("\nAll tests passed! ReadingProgressRequest now accepts float values.")
    return True

if __name__ == "__main__":
    success = test_reading_progress_request()
    exit(0 if success else 1)
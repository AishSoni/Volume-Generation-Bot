#!/usr/bin/env python3
"""
Test script to verify validation catches invalid configurations
"""

from config import BotConfig

def test_validation_scenarios():
    """Test various validation scenarios"""
    print("="*70)
    print("Testing Configuration Validation Edge Cases")
    print("="*70)
    
    test_cases = [
        {
            "name": "Valid configuration",
            "min_open": 80,
            "max_open": 120,
            "min_close": 30,
            "max_close": 50,
            "should_pass": True
        },
        {
            "name": "Insufficient buffer (exactly 30s)",
            "min_open": 80,
            "max_open": 120,
            "min_close": 30,
            "max_close": 50,
            "should_pass": True  # Exactly 30s buffer should pass
        },
        {
            "name": "Insufficient buffer (29s - should FAIL)",
            "min_open": 79,
            "max_open": 120,
            "min_close": 30,
            "max_close": 50,
            "should_pass": False
        },
        {
            "name": "Min > Max for open delays (should FAIL)",
            "min_open": 120,
            "max_open": 80,
            "min_close": 30,
            "max_close": 50,
            "should_pass": False
        },
        {
            "name": "Min > Max for close delays (should FAIL)",
            "min_open": 80,
            "max_open": 120,
            "min_close": 60,
            "max_close": 30,
            "should_pass": False
        },
        {
            "name": "Large buffer (safe)",
            "min_open": 150,
            "max_open": 300,
            "min_close": 30,
            "max_close": 50,
            "should_pass": True
        },
        {
            "name": "Negative values (should FAIL)",
            "min_open": -10,
            "max_open": 120,
            "min_close": 30,
            "max_close": 50,
            "should_pass": False
        },
    ]
    
    passed = 0
    failed = 0
    
    for i, test in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test['name']}")
        print(f"  Settings: MIN_OPEN={test['min_open']}, MAX_OPEN={test['max_open']}, "
              f"MIN_CLOSE={test['min_close']}, MAX_CLOSE={test['max_close']}")
        
        # Calculate buffer
        buffer = test['min_open'] - test['max_close']
        print(f"  Buffer: {buffer}s")
        
        # Create a config object with test values
        # We need to bypass the from_env() to inject test values
        try:
            # Create a minimal config for testing validation only
            from dataclasses import replace
            import os
            from dotenv import load_dotenv
            
            load_dotenv()
            
            # Load base config from env
            base_config = BotConfig.from_env()
            
            # Replace with test values
            test_config = replace(
                base_config,
                min_open_delay=test['min_open'],
                max_open_delay=test['max_open'],
                min_close_delay=test['min_close'],
                max_close_delay=test['max_close']
            )
            
            # Run validation
            test_config.validate()
            
            if test['should_pass']:
                print(f"  ✅ PASS: Validation passed as expected")
                passed += 1
            else:
                print(f"  ❌ FAIL: Validation should have failed but passed!")
                failed += 1
                
        except ValueError as e:
            if not test['should_pass']:
                print(f"  ✅ PASS: Validation correctly failed with: {e}")
                passed += 1
            else:
                print(f"  ❌ FAIL: Validation failed when it should pass: {e}")
                failed += 1
        except Exception as e:
            print(f"  ❌ ERROR: Unexpected exception: {e}")
            failed += 1
    
    print(f"\n{'='*70}")
    print("Test Results")
    print("="*70)
    print(f"Passed: {passed}/{len(test_cases)}")
    print(f"Failed: {failed}/{len(test_cases)}")
    
    if failed == 0:
        print(f"\n✅ All validation tests passed!")
        return True
    else:
        print(f"\n❌ Some tests failed")
        return False


if __name__ == "__main__":
    import sys
    success = test_validation_scenarios()
    sys.exit(0 if success else 1)

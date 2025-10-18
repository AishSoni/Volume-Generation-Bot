#!/usr/bin/env python3
"""
Test script to verify random interval functionality
Tests the configuration validation for MIN_OPEN_DELAY and MAX_CLOSE_DELAY
"""

import sys
from dotenv import load_dotenv
from config import BotConfig

# Explicitly load .env file
load_dotenv()

def test_random_intervals():
    """Test the random interval configuration and validation"""
    print("="*70)
    print("Testing Random Interval Configuration")
    print("="*70)
    
    try:
        # Load configuration
        config = BotConfig.from_env()
        
        print(f"\nConfiguration loaded:")
        print(f"  MIN_OPEN_DELAY: {config.min_open_delay}s")
        print(f"  MAX_OPEN_DELAY: {config.max_open_delay}s")
        print(f"  MIN_CLOSE_DELAY: {config.min_close_delay}s")
        print(f"  MAX_CLOSE_DELAY: {config.max_close_delay}s")
        
        print(f"\nValidation checks:")
        
        # Check 1: Open delay range is valid
        if config.min_open_delay <= config.max_open_delay:
            print(f"  ✅ Open delay range is valid: {config.min_open_delay}s - {config.max_open_delay}s")
        else:
            print(f"  ❌ Open delay range is invalid: MIN > MAX")
        
        # Check 2: Close delay range is valid
        if config.min_close_delay <= config.max_close_delay:
            print(f"  ✅ Close delay range is valid: {config.min_close_delay}s - {config.max_close_delay}s")
        else:
            print(f"  ❌ Close delay range is invalid: MIN > MAX")
        
        # Check 3: Safety buffer validation
        safety_buffer = 30
        required_min_open = config.max_close_delay + safety_buffer
        actual_buffer = config.min_open_delay - config.max_close_delay
        
        print(f"\n{'='*70}")
        print("Safety Buffer Validation")
        print("="*70)
        print(f"  MAX_CLOSE_DELAY: {config.max_close_delay}s")
        print(f"  Required safety buffer: {safety_buffer}s")
        print(f"  Required MIN_OPEN_DELAY: >= {required_min_open}s")
        print(f"  Actual MIN_OPEN_DELAY: {config.min_open_delay}s")
        print(f"  Actual buffer: {actual_buffer}s")
        
        if config.min_open_delay >= required_min_open:
            print(f"\n  ✅ PASS: Safety buffer of {actual_buffer}s ensures trades won't overlap")
            print(f"     New trades will only open after positions close ({config.max_close_delay}s)")
            print(f"     Plus {actual_buffer}s buffer for processing")
        else:
            print(f"\n  ❌ FAIL: Insufficient safety buffer!")
            print(f"     Risk: New trades could open before old positions close")
            print(f"     Solution: Increase MIN_OPEN_DELAY to at least {required_min_open}s")
            return False
        
        # Run full validation
        print(f"\n{'='*70}")
        print("Running Full Validation")
        print("="*70)
        
        try:
            config.validate()
            print(f"  ✅ All configuration validation checks passed!")
        except ValueError as e:
            print(f"  ❌ Validation failed: {e}")
            return False
        
        # Demonstrate random selection
        print(f"\n{'='*70}")
        print("Random Interval Simulation")
        print("="*70)
        print(f"\nSimulating 10 random selections:")
        print(f"\nOpen delays (time until next trade):")
        
        import random
        open_delays = [random.randint(config.min_open_delay, config.max_open_delay) for _ in range(10)]
        close_delays = [random.randint(config.min_close_delay, config.max_close_delay) for _ in range(10)]
        
        for i, (open_d, close_d) in enumerate(zip(open_delays, close_delays), 1):
            total_cycle = open_d + close_d
            print(f"  Trade {i}: Wait {open_d}s → Open → Hold {close_d}s → Close (Total: {total_cycle}s)")
        
        avg_open = sum(open_delays) / len(open_delays)
        avg_close = sum(close_delays) / len(close_delays)
        avg_cycle = avg_open + avg_close
        
        print(f"\nAverages:")
        print(f"  Open delay: {avg_open:.1f}s (range: {config.min_open_delay}-{config.max_open_delay}s)")
        print(f"  Close delay: {avg_close:.1f}s (range: {config.min_close_delay}-{config.max_close_delay}s)")
        print(f"  Total cycle time: {avg_cycle:.1f}s (~{avg_cycle/60:.1f} minutes)")
        
        print(f"\n{'='*70}")
        print("Summary")
        print("="*70)
        print(f"✅ Configuration is valid and safe!")
        print(f"✅ Random intervals will provide natural variation")
        print(f"✅ Safety buffer prevents trade overlap")
        print(f"\nThe bot will:")
        print(f"  1. Open a trade")
        print(f"  2. Close after {config.min_close_delay}-{config.max_close_delay}s (random)")
        print(f"  3. Wait {config.min_open_delay}-{config.max_open_delay}s before next trade (random)")
        print(f"  4. Repeat")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_random_intervals()
    sys.exit(0 if success else 1)

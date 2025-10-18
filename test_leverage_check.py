#!/usr/bin/env python3
"""
Test script to verify leverage limit checking from Lighter API
"""

import asyncio
import sys
from dotenv import load_dotenv
from config import BotConfig

# Explicitly load .env file
load_dotenv()

async def test_leverage_check():
    """Test the leverage checking functionality"""
    print("="*70)
    print("Testing Leverage Limit Check from Lighter API")
    print("="*70)
    
    try:
        # Load configuration
        config = BotConfig.from_env()
        
        print(f"\nConfiguration loaded:")
        print(f"  Base URL: {config.base_url}")
        print(f"  Market Index: {config.market_index}")
        print(f"  Configured Leverage: {config.leverage}x")
        
        # Fetch max leverage from API
        print(f"\nFetching market details from Lighter API...")
        max_leverage = await config.get_market_max_leverage()
        
        print(f"\n✅ Successfully fetched market information:")
        print(f"  Market {config.market_index} maximum leverage: {max_leverage}x")
        print(f"  Your configured leverage: {config.leverage}x")
        
        # Validate
        if config.leverage <= max_leverage:
            print(f"\n✅ PASS: Your leverage ({config.leverage}x) is within the allowed limit ({max_leverage}x)")
        else:
            print(f"\n❌ FAIL: Your leverage ({config.leverage}x) exceeds the maximum allowed ({max_leverage}x)")
            print(f"   Please update LEVERAGE in your .env file to {max_leverage} or lower.")
            return False
        
        # Run full validation
        print(f"\nRunning full validation with API checks...")
        await config.validate_with_api()
        print(f"✅ All validations passed!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_leverage_check())
    sys.exit(0 if success else 1)

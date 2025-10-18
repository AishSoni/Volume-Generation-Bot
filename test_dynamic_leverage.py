#!/usr/bin/env python3
"""
Test script to verify dynamic leverage functionality
"""

import asyncio
import sys
from dotenv import load_dotenv
from config import BotConfig

# Explicitly load .env file
load_dotenv()

async def test_dynamic_leverage():
    """Test the dynamic leverage functionality"""
    print("="*70)
    print("Testing Dynamic Leverage Feature")
    print("="*70)
    
    try:
        # Load configuration
        config = BotConfig.from_env()
        
        print(f"\nConfiguration loaded:")
        print(f"  Base URL: {config.base_url}")
        print(f"  Market Whitelist: {config.market_whitelist}")
        print(f"  Dynamic Leverage: {config.use_dynamic_leverage}")
        print(f"  Leverage Buffer: {config.leverage_buffer}x")
        print(f"  Base Leverage: {config.leverage}x")
        
        # Validate all whitelisted markets
        print(f"\nValidating markets and fetching max leverage...")
        await config.validate_with_api()
        
        if not config.use_dynamic_leverage:
            print(f"\n⚠️  Dynamic leverage is DISABLED")
            print(f"   All trades will use fixed leverage: {config.leverage}x")
            print(f"\n   To enable, set USE_DYNAMIC_LEVERAGE=true in .env")
            return True
        
        print(f"\n✅ Dynamic leverage is ENABLED")
        print(f"\n{'='*70}")
        print("Dynamic Leverage Simulation")
        print("="*70)
        
        # Simulate leverage selection for each market
        for market_id in config.market_whitelist:
            print(f"\nMarket {market_id}:")
            try:
                market_info = await config.get_market_info(market_id)
                symbol = market_info['symbol']
                max_leverage = market_info['max_leverage']
                
                print(f"  Symbol: {symbol}")
                print(f"  Max Leverage: {max_leverage}x")
                
                min_leverage = max(1, max_leverage - config.leverage_buffer)
                print(f"  Dynamic Range: {min_leverage}x - {max_leverage}x")
                
                # Simulate 10 random selections
                print(f"  Simulating 10 random leverage selections:")
                leverage_counts = {}
                for i in range(10):
                    selected = config.calculate_dynamic_leverage(max_leverage)
                    leverage_counts[selected] = leverage_counts.get(selected, 0) + 1
                
                # Display results
                for lev in sorted(leverage_counts.keys()):
                    count = leverage_counts[lev]
                    bar = "█" * count
                    print(f"    {lev}x: {bar} ({count}/10)")
                    
            except Exception as e:
                print(f"  ❌ Error: {e}")
        
        # Test asymmetric leverage (different for each account)
        print(f"\n{'='*70}")
        print("Asymmetric Leverage Simulation")
        print("="*70)
        print("\nIn dynamic mode, each account gets DIFFERENT random leverage:")
        print("(This creates asymmetric positions while maintaining delta-neutral)")
        
        # Demonstrate on first 3 markets
        sample_markets = config.market_whitelist[:min(3, len(config.market_whitelist))]
        for market_id in sample_markets:
            try:
                market_info = await config.get_market_info(market_id)
                symbol = market_info['symbol']
                max_leverage = market_info['max_leverage']
                
                print(f"\nMarket {market_id} ({symbol}):")
                print(f"  Simulating 3 trades with asymmetric leverage:")
                
                for i in range(3):
                    # Each account independently selects leverage
                    long_leverage = config.calculate_dynamic_leverage(max_leverage)
                    short_leverage = config.calculate_dynamic_leverage(max_leverage)
                    
                    asymmetric = "✓ Different" if long_leverage != short_leverage else "○ Same (random)"
                    print(f"    Trade {i+1}: Long {long_leverage}x | Short {short_leverage}x  [{asymmetric}]")
                    
            except Exception as e:
                print(f"  ❌ Error: {e}")
        
        print(f"\n{'='*70}")
        print("How Dynamic Leverage Works")
        print("="*70)
        print("• Each trade randomly selects leverage within the market's range")
        print("• Range: (max_leverage - buffer) to max_leverage")
        print(f"• Your buffer: {config.leverage_buffer}x")
        print("• Each ACCOUNT gets different random leverage per trade")
        print("• This creates asymmetric positions (e.g., Long 25x vs Short 20x)")
        print("• Both positions maintain same notional value for delta-neutral")
        print("• Leverage is updated independently for each account before trade")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_dynamic_leverage())
    sys.exit(0 if success else 1)

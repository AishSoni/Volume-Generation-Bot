#!/usr/bin/env python3
"""
Discover High-Liquidity Markets on Lighter DEX

This script queries the Lighter API to find all available markets,
calculates their liquidity metrics, and displays leverage limits.
"""

import asyncio
import os
from dotenv import load_dotenv
import lighter

load_dotenv()


async def discover_markets():
    """Query Lighter API and analyze all markets for liquidity and leverage"""
    
    print("="*80)
    print("LIGHTER DEX MARKET DISCOVERY & LIQUIDITY ANALYSIS")
    print("="*80)
    
    base_url = os.getenv('BASE_URL', 'https://mainnet.zklighter.elliot.ai')
    print(f"\nNetwork: {base_url}")
    print("\nFetching market data from Lighter API...")
    
    try:
        configuration = lighter.Configuration(base_url)
        api_client = lighter.ApiClient(configuration)
        order_api = lighter.OrderApi(api_client)
        
        # Get all order book details
        order_book_details_response = await order_api.order_book_details()
        
        if not order_book_details_response.order_book_details:
            print("❌ No market data available")
            await api_client.close()
            return
        
        markets_data = []
        
        print(f"✅ Found {len(order_book_details_response.order_book_details)} markets\n")
        print("Analyzing liquidity for each market...")
        
        # Analyze each market
        for detail in order_book_details_response.order_book_details:
            market_id = detail.market_id
            symbol = detail.symbol
            
            # Calculate max leverage from min_initial_margin_fraction
            # min_initial_margin_fraction is in basis points (1/10000)
            min_margin_fraction = detail.min_initial_margin_fraction / 10000.0
            
            # Handle edge case: if min_margin_fraction is 0, skip leverage calculation
            if min_margin_fraction > 0:
                max_leverage = int(1.0 / min_margin_fraction)
            else:
                max_leverage = 0  # Market doesn't support leverage or is disabled
            
            # Get order book depth to measure liquidity
            try:
                order_book = await order_api.order_book_orders(market_id=market_id, limit=10)
                
                # Calculate liquidity metrics
                bid_liquidity = 0
                ask_liquidity = 0
                best_bid = 0
                best_ask = 0
                
                if order_book.bids and len(order_book.bids) > 0:
                    best_bid = float(order_book.bids[0].price)
                    # Sum up liquidity in top 10 bids
                    # Note: SimpleOrder uses 'amount_base' not 'amount'
                    for bid in order_book.bids[:10]:
                        bid_liquidity += float(bid.price) * float(bid.amount_base)
                
                if order_book.asks and len(order_book.asks) > 0:
                    best_ask = float(order_book.asks[0].price)
                    # Sum up liquidity in top 10 asks
                    for ask in order_book.asks[:10]:
                        ask_liquidity += float(ask.price) * float(ask.amount_base)
                
                # Calculate spread
                spread_pct = 0
                if best_bid > 0 and best_ask > 0:
                    spread_pct = ((best_ask - best_bid) / best_ask) * 100
                
                # Total liquidity (combined bid + ask)
                total_liquidity = bid_liquidity + ask_liquidity
                
                markets_data.append({
                    'market_id': market_id,
                    'symbol': symbol,
                    'max_leverage': max_leverage,
                    'best_bid': best_bid,
                    'best_ask': best_ask,
                    'spread_pct': spread_pct,
                    'bid_liquidity': bid_liquidity,
                    'ask_liquidity': ask_liquidity,
                    'total_liquidity': total_liquidity,
                    'size_decimals': detail.size_decimals,
                    'price_decimals': detail.price_decimals
                })
                
            except Exception as e:
                # If we can't fetch order book, still include the market with zero liquidity
                markets_data.append({
                    'market_id': market_id,
                    'symbol': symbol,
                    'max_leverage': max_leverage,
                    'best_bid': 0,
                    'best_ask': 0,
                    'spread_pct': 0,
                    'bid_liquidity': 0,
                    'ask_liquidity': 0,
                    'total_liquidity': 0,
                    'size_decimals': detail.size_decimals,
                    'price_decimals': detail.price_decimals
                })
        
        # Close API client properly
        await api_client.close()
        
        # Filter out markets with no leverage (disabled or invalid)
        markets_data = [m for m in markets_data if m['max_leverage'] > 0]
        
        # Sort by total liquidity (descending)
        markets_data.sort(key=lambda x: x['total_liquidity'], reverse=True)
        
        # Display results
        print("\n" + "="*80)
        print("MARKET ANALYSIS RESULTS (Sorted by Liquidity)")
        print("="*80)
        
        print("\n{:<4} {:<12} {:<8} {:<12} {:<12} {:<10} {:<15}".format(
            "ID", "Symbol", "Leverage", "Best Bid", "Best Ask", "Spread %", "Liquidity ($)"
        ))
        print("-"*80)
        
        for market in markets_data:
            liquidity_str = f"${market['total_liquidity']:,.0f}" if market['total_liquidity'] > 0 else "N/A"
            bid_str = f"${market['best_bid']:,.2f}" if market['best_bid'] > 0 else "N/A"
            ask_str = f"${market['best_ask']:,.2f}" if market['best_ask'] > 0 else "N/A"
            spread_str = f"{market['spread_pct']:.4f}%" if market['spread_pct'] > 0 else "N/A"
            
            print("{:<4} {:<12} {:<8} {:<12} {:<12} {:<10} {:<15}".format(
                market['market_id'],
                market['symbol'],
                f"{market['max_leverage']}x",
                bid_str,
                ask_str,
                spread_str,
                liquidity_str
            ))
        
        # Categorize markets by liquidity
        print("\n" + "="*80)
        print("LIQUIDITY CATEGORIES")
        print("="*80)
        
        high_liquidity = [m for m in markets_data if m['total_liquidity'] >= 50000]
        medium_liquidity = [m for m in markets_data if 10000 <= m['total_liquidity'] < 50000]
        low_liquidity = [m for m in markets_data if 0 < m['total_liquidity'] < 10000]
        no_data = [m for m in markets_data if m['total_liquidity'] == 0]
        
        print(f"\n🟢 HIGH LIQUIDITY (>= $50,000 in order book):")
        if high_liquidity:
            for m in high_liquidity:
                print(f"   Market {m['market_id']:2d} ({m['symbol']:8s}): ${m['total_liquidity']:>10,.0f} | "
                      f"{m['max_leverage']:2d}x leverage | Spread: {m['spread_pct']:.4f}%")
        else:
            print("   None")
        
        print(f"\n🟡 MEDIUM LIQUIDITY ($10,000 - $50,000):")
        if medium_liquidity:
            for m in medium_liquidity:
                print(f"   Market {m['market_id']:2d} ({m['symbol']:8s}): ${m['total_liquidity']:>10,.0f} | "
                      f"{m['max_leverage']:2d}x leverage | Spread: {m['spread_pct']:.4f}%")
        else:
            print("   None")
        
        print(f"\n🔴 LOW LIQUIDITY (< $10,000):")
        if low_liquidity:
            for m in low_liquidity:
                print(f"   Market {m['market_id']:2d} ({m['symbol']:8s}): ${m['total_liquidity']:>10,.0f} | "
                      f"{m['max_leverage']:2d}x leverage | Spread: {m['spread_pct']:.4f}%")
        else:
            print("   None")
        
        if no_data:
            print(f"\n⚫ NO DATA AVAILABLE ({len(no_data)} markets)")
        
        # Recommendations for volume bot
        print("\n" + "="*80)
        print("RECOMMENDATIONS FOR VOLUME GENERATION")
        print("="*80)
        
        # Filter for good markets: high liquidity + low spread
        excellent_markets = [
            m for m in high_liquidity 
            if m['spread_pct'] < 0.05 and m['spread_pct'] > 0
        ]
        
        good_markets = [
            m for m in high_liquidity 
            if 0.05 <= m['spread_pct'] < 0.1
        ]
        
        print("\n✅ EXCELLENT MARKETS (High liquidity + <0.05% spread):")
        if excellent_markets:
            market_ids = [str(m['market_id']) for m in excellent_markets]
            print(f"\n   Recommended MARKET_WHITELIST={','.join(market_ids)}")
            print("\n   Details:")
            for m in excellent_markets:
                dynamic_range = f"{max(1, m['max_leverage']-5)}-{m['max_leverage']}"
                print(f"   • Market {m['market_id']} ({m['symbol']}): "
                      f"{m['max_leverage']}x max leverage, "
                      f"${m['total_liquidity']:,.0f} liquidity, "
                      f"{m['spread_pct']:.4f}% spread")
                print(f"     Dynamic leverage range: {dynamic_range}x")
        else:
            print("   None found with spread < 0.05%")
        
        print("\n⚠️  ACCEPTABLE MARKETS (High liquidity + 0.05-0.1% spread):")
        if good_markets:
            for m in good_markets:
                print(f"   • Market {m['market_id']} ({m['symbol']}): "
                      f"{m['max_leverage']}x max leverage, "
                      f"${m['total_liquidity']:,.0f} liquidity, "
                      f"{m['spread_pct']:.4f}% spread")
        else:
            print("   None")
        
        # Show markets by leverage
        print("\n" + "="*80)
        print("MARKETS BY LEVERAGE TIER")
        print("="*80)
        
        leverage_50x = [m for m in markets_data if m['max_leverage'] >= 50]
        leverage_20x = [m for m in markets_data if 20 <= m['max_leverage'] < 50]
        leverage_10x = [m for m in markets_data if 10 <= m['max_leverage'] < 20]
        leverage_low = [m for m in markets_data if m['max_leverage'] < 10]
        
        print(f"\n⚡ 50x+ LEVERAGE:")
        if leverage_50x:
            for m in leverage_50x:
                liq_str = f"${m['total_liquidity']:,.0f}" if m['total_liquidity'] > 0 else "N/A"
                print(f"   Market {m['market_id']:2d} ({m['symbol']:8s}): {m['max_leverage']}x | Liquidity: {liq_str}")
        
        print(f"\n⚡ 20-49x LEVERAGE:")
        if leverage_20x:
            for m in leverage_20x:
                liq_str = f"${m['total_liquidity']:,.0f}" if m['total_liquidity'] > 0 else "N/A"
                print(f"   Market {m['market_id']:2d} ({m['symbol']:8s}): {m['max_leverage']}x | Liquidity: {liq_str}")
        
        print(f"\n⚡ 10-19x LEVERAGE:")
        if leverage_10x:
            for m in leverage_10x:
                liq_str = f"${m['total_liquidity']:,.0f}" if m['total_liquidity'] > 0 else "N/A"
                print(f"   Market {m['market_id']:2d} ({m['symbol']:8s}): {m['max_leverage']}x | Liquidity: {liq_str}")
        
        if leverage_low:
            print(f"\n⚡ <10x LEVERAGE ({len(leverage_low)} markets)")
        
        # Export configuration
        print("\n" + "="*80)
        print("CONFIGURATION EXPORT")
        print("="*80)
        
        if excellent_markets:
            print("\n# Copy this to your .env file:")
            print(f"MARKET_WHITELIST={','.join([str(m['market_id']) for m in excellent_markets])}")
            print("\n# Market details:")
            for m in excellent_markets:
                print(f"#   ✅ Market {m['market_id']} ({m['symbol']}): "
                      f"Max leverage {m['max_leverage']}x, "
                      f"Dynamic range: {max(1, m['max_leverage']-5)}-{m['max_leverage']}x")
        
        print("\n" + "="*80)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(discover_markets())

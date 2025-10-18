#!/usr/bin/env python3
"""
Test script to verify dynamic precision calculation for different asset prices
"""

def calculate_precision(price: float) -> tuple[int, int]:
    """
    Calculate precision decimals and multiplier based on asset price
    
    Returns:
        tuple: (precision_decimals, precision_multiplier)
    """
    if price >= 10000:  # BTC-like (>$10k)
        precision_decimals = 5
    elif price >= 1000:  # ETH-like ($1k-$10k)
        precision_decimals = 4
    elif price >= 100:  # SOL-like ($100-$1k)
        precision_decimals = 3
    elif price >= 10:  # Mid-range ($10-$100)
        precision_decimals = 2
    else:  # Low-priced (<$10)
        precision_decimals = 1
    
    precision_multiplier = 10 ** precision_decimals
    return precision_decimals, precision_multiplier


def test_precision_for_assets():
    """Test precision calculation for various assets"""
    print("="*80)
    print("Dynamic Precision Testing for Different Asset Prices")
    print("="*80)
    
    # Test cases with realistic prices
    test_cases = [
        ("BTC", 107000.0, 2.0, 50),
        ("ETH", 3500.0, 2.0, 50),
        ("BNB", 650.0, 2.0, 20),
        ("SOL", 150.0, 2.0, 25),
        ("AVAX", 40.0, 2.0, 10),
        ("DOGE", 0.15, 2.0, 10),
        ("XRP", 2.5, 2.0, 20),
        ("LTC", 95.0, 2.0, 10),
    ]
    
    for asset_name, price, margin_target, leverage in test_cases:
        print(f"\n{'-'*80}")
        print(f"Asset: {asset_name}")
        print(f"  Price: ${price:.2f}")
        print(f"  Target margin: ${margin_target:.2f}")
        print(f"  Leverage: {leverage}x")
        
        # Calculate precision
        precision_decimals, precision_multiplier = calculate_precision(price)
        
        print(f"  Precision: {precision_decimals} decimals (multiplier: {precision_multiplier})")
        
        # Calculate target notional
        target_notional = margin_target * leverage
        
        # Calculate asset amount needed
        asset_amount = target_notional / price
        
        # Calculate base_amount with proper precision
        base_amount = max(1, round(asset_amount * precision_multiplier))
        
        # Calculate actual values
        actual_asset_amount = base_amount / precision_multiplier
        actual_notional = actual_asset_amount * price
        actual_margin = actual_notional / leverage
        
        print(f"  Target notional: ${target_notional:.2f}")
        print(f"  Asset amount needed: {asset_amount:.{precision_decimals+2}f} {asset_name}")
        print(f"  base_amount (internal): {base_amount}")
        print(f"  Actual asset amount: {actual_asset_amount:.{precision_decimals}f} {asset_name}")
        print(f"  Actual notional: ${actual_notional:.2f}")
        print(f"  Actual margin: ${actual_margin:.2f}")
        print(f"  Error: ${abs(actual_margin - margin_target):.2f}")
        
        # Validation
        error_percentage = abs(actual_margin - margin_target) / margin_target * 100
        if error_percentage <= 10:  # Allow 10% error due to rounding
            print(f"  ✅ PASS: Error {error_percentage:.1f}% is within acceptable range")
        else:
            print(f"  ⚠️  WARNING: Error {error_percentage:.1f}% exceeds 10%")
    
    print(f"\n{'='*80}")
    print("Summary")
    print("="*80)
    print("The precision system automatically adjusts based on asset price:")
    print("  • BTC (~$100k):    5 decimals → 1 unit = 0.00001 BTC = ~$1")
    print("  • ETH (~$3k):      4 decimals → 1 unit = 0.0001 ETH = ~$0.30")
    print("  • SOL (~$150):     3 decimals → 1 unit = 0.001 SOL = ~$0.15")
    print("  • AVAX (~$40):     2 decimals → 1 unit = 0.01 AVAX = ~$0.40")
    print("  • DOGE (~$0.15):   1 decimal  → 1 unit = 0.1 DOGE = ~$0.015")
    print("\nThis ensures optimal precision for all asset price ranges!")


if __name__ == "__main__":
    test_precision_for_assets()

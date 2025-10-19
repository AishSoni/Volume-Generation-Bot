"""
Calculate optimal timing for maximum volume generation with minimal bleed
"""

# Current constraints
limit_order_wait = 90  # seconds to wait for limit order fill
limit_order_retry_wait = 45  # seconds for retry attempt
total_limit_wait = limit_order_wait + limit_order_retry_wait  # 135s max

# Position lifecycle
min_close = 30  # Current minimum close time
max_close = 50  # Current maximum close time

# Calculate minimum safe open delay
# Rule: New trade must start AFTER previous positions close
# Safety buffer to prevent overlap
safety_buffer = 10  # seconds

# For limit orders (80% of trades):
# Trade opens -> Wait up to 135s for fill -> Position holds 30-50s -> Position closes
# Total cycle: 135s + 50s = 185s worst case

# For market orders (20% of trades):
# Trade opens instantly -> Position holds 30-50s -> Position closes  
# Total cycle: 50s worst case

# Minimum safe delay between trade STARTS:
# Must be > max_close to ensure positions close before new ones open
min_safe_open_delay = max_close + safety_buffer  # 60s

# But we also want limit orders to have time to fill before opening new trades
# This prevents having too many pending limit orders at once

print("="*70)
print("OPTIMAL TIMING CALCULATION FOR MAXIMUM VOLUME")
print("="*70)

print("\n=== Current Setup ===")
print(f"Limit order wait time: {limit_order_wait}s")
print(f"Limit order retry wait: {limit_order_retry_wait}s")
print(f"Total limit order cycle: {total_limit_wait}s")
print(f"Position close delay: {min_close}-{max_close}s")

print("\n=== Volume Calculation ===")

# Scenario 1: Maximum speed (risky - might overlap)
scenario1_open_delay = 60
scenario1_cycle = scenario1_open_delay + max_close
scenario1_trades_per_hour = 3600 / scenario1_cycle
print(f"\nScenario 1: AGGRESSIVE (Min delay: {scenario1_open_delay}s)")
print(f"  Full cycle: {scenario1_cycle}s")
print(f"  Trades/hour: {scenario1_trades_per_hour:.1f}")
print(f"  ⚠️  Risk: Limit orders may overlap with new trades")

# Scenario 2: Balanced (recommended)
scenario2_open_delay = 90
scenario2_cycle = scenario2_open_delay + max_close  
scenario2_trades_per_hour = 3600 / scenario2_cycle
print(f"\nScenario 2: BALANCED (Min delay: {scenario2_open_delay}s)")
print(f"  Full cycle: {scenario2_cycle}s")
print(f"  Trades/hour: {scenario2_trades_per_hour:.1f}")
print(f"  ✅ Balance of speed and safety")

# Scenario 3: Conservative (safest)
scenario3_open_delay = 150
scenario3_cycle = scenario3_open_delay + max_close
scenario3_trades_per_hour = 3600 / scenario3_cycle
print(f"\nScenario 3: CONSERVATIVE (Min delay: {scenario3_open_delay}s)")
print(f"  Full cycle: {scenario3_cycle}s")
print(f"  Trades/hour: {scenario3_trades_per_hour:.1f}")
print(f"  ✅ Safest, allows all limit orders to fully process")

# Scenario 4: MAXIMUM VOLUME with shorter limit waits
scenario4_limit_wait = 60
scenario4_retry_wait = 30
scenario4_open_delay = 70
scenario4_cycle = scenario4_open_delay + max_close
scenario4_trades_per_hour = 3600 / scenario4_cycle
print(f"\nScenario 4: MAXIMUM VOLUME (Optimized)")
print(f"  Limit wait: {scenario4_limit_wait}s (instead of 90s)")
print(f"  Retry wait: {scenario4_retry_wait}s (instead of 45s)")
print(f"  Open delay: {scenario4_open_delay}s")
print(f"  Full cycle: {scenario4_cycle}s")
print(f"  Trades/hour: {scenario4_trades_per_hour:.1f}")
print(f"  ✅ Maximum speed with acceptable fill rate")

print("\n=== Volume Per Hour Comparison ===")
print(f"Your old settings (80s open delay): {3600/(80+50):.1f} trades/hour")
print(f"Scenario 1 (Aggressive):            {scenario1_trades_per_hour:.1f} trades/hour")
print(f"Scenario 2 (Balanced):              {scenario2_trades_per_hour:.1f} trades/hour")
print(f"Scenario 4 (Max Volume):            {scenario4_trades_per_hour:.1f} trades/hour")

print("\n=== Recommended: MAXIMUM VOLUME Configuration ===")
print("This optimizes for speed while maintaining high limit order fill rate:\n")
print("MIN_OPEN_DELAY=70")
print("MAX_OPEN_DELAY=100")
print("MIN_CLOSE_DELAY=30")
print("MAX_CLOSE_DELAY=50")
print("LIMIT_ORDER_WAIT_TIME=60")
print("LIMIT_ORDER_PROBABILITY=0.8")
print("LIMIT_ORDER_RETRY_ADJUSTMENT=0.0003  # Slightly more aggressive")

print("\n=== Expected Results ===")
margin_per_trade = 2  # $2 USDT margin per account
leverage = 10
notional_per_trade = margin_per_trade * 2 * leverage  # $40 total notional
trades_per_hour_optimized = scenario4_trades_per_hour

print(f"Margin per trade: ${margin_per_trade * 2} ($2 per account)")
print(f"Notional per trade: ${notional_per_trade} (at {leverage}x leverage)")
print(f"Trades per hour: {trades_per_hour_optimized:.1f}")
print(f"Volume per hour: ${notional_per_trade * trades_per_hour_optimized:.0f}")
print(f"Volume per day: ${notional_per_trade * trades_per_hour_optimized * 24:.0f}")
print(f"\nWith 80% limit orders: Should be breakeven or slight profit")
print(f"With old 100% market: Would bleed ~${0.028 * trades_per_hour_optimized * 24:.2f}/day")

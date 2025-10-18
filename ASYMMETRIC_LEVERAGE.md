# Asymmetric Leverage Feature

## Overview

The asymmetric leverage feature extends the dynamic leverage mode to use **different random leverage values** for each account in a delta-neutral trade. This creates position asymmetry while maintaining the same notional value.

## How It Works

### Traditional Dynamic Leverage (Previous)
- Both accounts used the SAME random leverage
- Example: Long 25x, Short 25x

### Asymmetric Dynamic Leverage (Current)
- Each account independently selects random leverage
- Example: Long 25x, Short 20x
- Both maintain same notional value ($100 in the example)

## Implementation Details

### Code Changes

1. **Leverage Calculation** (`delta_neutral_orchestrator.py`)
   ```python
   # Each account gets different leverage
   leverage_long = config.calculate_dynamic_leverage(market_max_leverage)
   leverage_short = config.calculate_dynamic_leverage(market_max_leverage)
   ```

2. **Independent Updates** (`update_leverage_for_accounts` method)
   - New method created to update leverage independently
   - Each account receives its own leverage value
   - Updates are performed in parallel for efficiency

3. **Enhanced Logging**
   - Shows both leverage values in trade execution
   - Example: `Long leverage: 25x | Short leverage: 20x`

## Configuration

Uses the same `.env` settings as dynamic leverage:

```env
USE_DYNAMIC_LEVERAGE=true  # Enable asymmetric leverage
LEVERAGE_BUFFER=5          # Buffer below max leverage
MARKET_WHITELIST=0,1,2,4,5,6,7,8,9  # Allowed markets
```

## Example Output

```
📊 Selected market: ETH (ID: 0)
   🎲 Dynamic leverage - Long: 48x | Short: 45x (max: 50x)

Executing delta neutral trade on ETH:
  Base amount: 0.0015
  Best Bid: $3,500.00, Best Ask: $3,502.00
  Spread: $2.00 (0.057%)
  Long leverage: 48x | Short leverage: 45x
```

## Benefits

1. **Increased Variability**: More diverse trading patterns
2. **Risk Distribution**: Different leverage ratios per trade
3. **Delta-Neutral Maintained**: Same notional value on both sides
4. **Natural Randomization**: Each account independently randomizes

## Testing

Run the test script to see asymmetric leverage in action:

```bash
python test_dynamic_leverage.py
```

The test demonstrates:
- Dynamic leverage ranges for each market
- Random leverage selection distribution
- **Asymmetric leverage simulation** showing different values per account

## Technical Notes

- Leverage is updated **before each trade** via isolated worker processes
- Each market has its own maximum leverage (fetched from Lighter API)
- Dynamic range: `(max_leverage - buffer)` to `max_leverage`
- Leverage values are independently randomized for each account
- Both positions maintain identical notional value for delta-neutral strategy

## When to Use

✅ **Use Asymmetric Leverage When:**
- You want maximum trading variation
- You want to simulate different trader behaviors
- You want more diverse position structures

❌ **Use Standard Dynamic Leverage When:**
- You prefer symmetrical positions
- You want simpler trade structures
- Set `USE_DYNAMIC_LEVERAGE=false` for fixed leverage across all trades

## Related Documentation

- `LEVERAGE_VALIDATION.md` - API-based leverage validation
- `MARKET_WHITELIST.md` - Market selection and whitelisting
- `USDT_SIZING_GUIDE.md` - Position sizing guide

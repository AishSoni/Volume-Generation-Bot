# Market Whitelist Feature

## Overview

The market whitelist feature allows you to specify multiple perpetual futures contracts (markets) that the bot can trade on. For each trade, the bot will **randomly select** a market from your whitelist, providing diversification and spreading trading volume across multiple markets.

## How It Works

### 1. **Configuration**

In your `.env` file, configure the `MARKET_WHITELIST` parameter:

```bash
# Single market (traditional behavior)
MARKET_WHITELIST=0

# Multiple markets - bot randomly picks one for each trade
MARKET_WHITELIST=0,1,2

# More markets for better diversification
MARKET_WHITELIST=0,1,2,3,4,5
```

### 2. **Random Selection**

For each trade cycle, the bot:
1. Randomly selects a market from your whitelist
2. Fetches the current price for that specific market
3. Executes the delta-neutral trade on the selected market
4. Tracks statistics per market

### 3. **Validation**

On startup, the bot validates ALL whitelisted markets:
- Checks that each market exists
- Verifies your configured leverage is within limits for EACH market
- Fetches market symbols (e.g., "ETH", "BTC") for better logging

If any market fails validation, the bot refuses to start.

## Configuration Examples

### Example 1: Single Market (Backwards Compatible)

```bash
# .env
MARKET_WHITELIST=0  # Only trade ETH-USD
LEVERAGE=20
```

**Result:** Bot always trades on Market 0 (ETH-USD), just like before.

### Example 2: Two Markets

```bash
# .env
MARKET_WHITELIST=0,1  # ETH-USD and BTC-USD
LEVERAGE=20
```

**Result:** Bot randomly alternates between ETH and BTC for each trade.

### Example 3: Multiple Markets

```bash
# .env
MARKET_WHITELIST=0,1,2,3,4  # 5 different markets
LEVERAGE=10
```

**Result:** Each trade is executed on a randomly selected market from the list.

### Example 4: Fallback Behavior

```bash
# .env
MARKET_WHITELIST=     # Empty or not set
MARKET_INDEX=0         # Fallback to this
```

**Result:** Bot uses only `MARKET_INDEX` (traditional single-market mode).

## Benefits

### 1. **Diversification**
Spread trading volume across multiple markets instead of concentrating on one.

### 2. **Risk Distribution**
Reduce the impact of issues with any single market (e.g., low liquidity, high volatility).

### 3. **Volume Distribution**
Avoid appearing as concentrated volume on a single market, which could affect market dynamics.

### 4. **Flexibility**
Easily adjust which markets to trade by updating the whitelist—no code changes needed.

## Bot Output Examples

### Startup Validation

```
Configuration:
  Base URL: https://mainnet.zklighter.elliot.ai
  Market Whitelist: [0, 1, 2] (3 market(s))
  Configured Leverage: 20x

Validating configuration against Lighter API...
Validating 3 whitelisted market(s)...
  ✅ Market 0 (ETH): Max leverage 50x
  ✅ Market 1 (BTC): Max leverage 50x
  ✅ Market 2 (SOL): Max leverage 25x
✅ All whitelisted markets validated successfully
```

### During Trading

```
==================================================
Trade #1
==================================================
📊 Selected market: BTC (ID: 1)
Using BASE_AMOUNT_IN_USDT: $100.00 @ $43250.50 = 0.0023 BTC
Executing delta neutral trade on BTC:
  Base amount: 0.0023
  Best Bid: $43245.00, Best Ask: $43250.00
  Spread: $5.00 (0.012%)
✅ Long order (Account 1): TX 1a2b3c4d5e6f7g8h...
✅ Short order (Account 2): TX 9h8g7f6e5d4c3b2a...
✅ Delta neutral trade executed successfully on BTC
📅 Position will close in 42 seconds
```

```
==================================================
Trade #2
==================================================
📊 Selected market: ETH (ID: 0)
Using BASE_AMOUNT_IN_USDT: $100.00 @ $2245.80 = 0.0445 ETH
Executing delta neutral trade on ETH:
  Base amount: 0.0445
  Best Bid: $2245.50, Best Ask: $2246.00
  Spread: $0.50 (0.022%)
✅ Delta neutral trade executed successfully on ETH
```

### Session Statistics

```
======================================================================
Market Statistics
======================================================================
  Market 0 (ETH): 15/18 trades (83.3% success)
  Market 1 (BTC): 12/14 trades (85.7% success)
  Market 2 (SOL): 8/10 trades (80.0% success)

Bot stopped
```

## Testing

### Test Market Whitelist Configuration

Run the test script to verify your whitelist setup:

```powershell
python test_market_whitelist.py
```

**Sample Output:**
```
Testing Market Whitelist Feature
=================================
Configuration loaded:
  Base URL: https://mainnet.zklighter.elliot.ai
  Market Whitelist: [0, 1]
  Number of markets: 2
  Configured Leverage: 20x

Validating all whitelisted markets...
  ✅ Market 0 (ETH): Max leverage 50x
  ✅ Market 1 (BTC): Max leverage 50x

✅ All validations passed!

Market Selection Demo:
  Trade 1: ETH (ID: 0)
  Trade 2: BTC (ID: 1)
  Trade 3: ETH (ID: 0)
  ...

Selection distribution:
  ETH (ID: 0): 6/10 (60%)
  BTC (ID: 1): 4/10 (40%)
```

## Important Notes

### Leverage Limits

Each market has its own maximum leverage. The bot validates your configured `LEVERAGE` against ALL whitelisted markets:

- ✅ If `LEVERAGE=20` and all markets support ≥20x, bot starts
- ❌ If `LEVERAGE=30` but Market 2 only supports 25x, bot refuses to start

**Error Example:**
```
❌ Validation failed: Leverage validation failed for one or more markets:
  - Market 2 (SOL): Leverage 30x exceeds max 25x
```

**Solution:** Either:
1. Lower `LEVERAGE` to 25 (or the lowest max among your markets)
2. Remove Market 2 from the whitelist

### Trade Size Considerations

- `BASE_AMOUNT` or `BASE_AMOUNT_IN_USDT` applies to ALL markets
- Different markets have different price scales (e.g., ETH ~$2000, BTC ~$40000)
- Using `BASE_AMOUNT_IN_USDT` is recommended for consistent dollar exposure across markets

**Example:**
```bash
BASE_AMOUNT_IN_USDT=100  # $100 per trade, regardless of market
```
- On ETH @ $2000: ~0.05 ETH
- On BTC @ $40000: ~0.0025 BTC
- On SOL @ $100: ~1.0 SOL

### Random Distribution

The selection is **truly random** for each trade. Over many trades, you'll see approximately equal distribution across markets, but short-term runs (e.g., 5 ETH trades in a row) are possible and normal.

## Backwards Compatibility

The feature is **fully backwards compatible**:

- If you don't set `MARKET_WHITELIST`, the bot uses `MARKET_INDEX` as a single-market whitelist
- Old `.env` files work without modification
- Behavior is identical to the previous version when using a single market

## Implementation Details

### Code Changes

1. **`config.py`:**
   - Added `market_whitelist` field
   - Added `parse_market_whitelist()` helper
   - Updated `get_market_max_leverage()` to accept `market_id` parameter
   - Added `get_market_info()` to fetch market symbols
   - Updated `validate_with_api()` to validate ALL whitelisted markets

2. **`delta_neutral_orchestrator.py`:**
   - Added `select_random_market()` method
   - Updated `get_current_price()` to accept `market_index` parameter
   - Modified `execute_delta_neutral_trade()` to select random market
   - Added per-market statistics tracking
   - Updated logging to show selected market for each trade

3. **`.env` and `.env.example`:**
   - Added `MARKET_WHITELIST` configuration option
   - Updated documentation

### Random Selection Algorithm

```python
def select_random_market(self) -> int:
    """Randomly select a market from the whitelist"""
    return random.choice(self.config.market_whitelist)
```

Uses Python's `random.choice()` for uniform random selection.

## Troubleshooting

### Error: "market_whitelist must contain at least one market"

**Cause:** Both `MARKET_WHITELIST` and `MARKET_INDEX` are missing or invalid.

**Solution:** Set either `MARKET_WHITELIST` or `MARKET_INDEX` in your `.env` file.

### Error: "Invalid MARKET_WHITELIST format"

**Cause:** Non-numeric values in whitelist.

**Bad:**
```bash
MARKET_WHITELIST=0,1,a,3  # 'a' is not a number
```

**Good:**
```bash
MARKET_WHITELIST=0,1,2,3
```

### Error: "Market X not found"

**Cause:** Market ID doesn't exist on the network (testnet vs mainnet).

**Solution:** 
1. Check available markets on your network (testnet/mainnet)
2. Remove invalid market IDs from the whitelist

### Markets Have Different Leverage Limits

**Issue:** You want to trade markets with different max leverage.

**Solution:** Set `LEVERAGE` to the **lowest** max leverage among your markets.

**Example:**
```
Market 0 (ETH): 50x max
Market 1 (BTC): 50x max  
Market 2 (SOL): 25x max  ← Lowest
```

Set `LEVERAGE=25` (or lower) to trade all three markets.

## Related Files

- `config.py` - Market whitelist parsing and validation
- `delta_neutral_orchestrator.py` - Random market selection logic
- `test_market_whitelist.py` - Test script for the feature
- `.env` - Your configuration with `MARKET_WHITELIST`
- `.env.example` - Example configuration

## FAQ

**Q: How many markets should I include?**  
A: Start with 2-3 major markets (ETH, BTC) for testing. Increase as you gain confidence.

**Q: Can I weight certain markets more heavily?**  
A: Not currently—selection is uniformly random. You can list a market multiple times in the whitelist for basic weighting: `MARKET_WHITELIST=0,0,1` gives Market 0 twice the probability.

**Q: Does this affect position closing?**  
A: No—positions are closed on the same market they were opened on. The bot tracks which market each position belongs to.

**Q: Can I change the whitelist while the bot is running?**  
A: No—restart the bot for whitelist changes to take effect.

**Q: What if a market becomes illiquid during trading?**  
A: The bot has spread checks that skip trades if the spread is too wide. Failed trades are logged but don't stop the bot.

**Q: Does this work on testnet?**  
A: Yes! Test with testnet markets before using on mainnet.

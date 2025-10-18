# USDT-Based Trade Sizing Guide

## Overview

You can now specify trade sizes in **USDT** instead of the base asset (ETH), making it much easier to understand and control your position sizes!

## How It Works

### Option 1: BASE_AMOUNT_IN_USDT (Recommended)

Specify your trade size in dollars:

```env
BASE_AMOUNT_IN_USDT=100  # $100 per trade
```

The bot will:
1. Fetch the current market price (mid-price between bid/ask)
2. Automatically convert $100 to the equivalent ETH amount
3. Execute the trade with that calculated amount

**Benefits:**
- ✅ Easy to understand ($100 is clear)
- ✅ Consistent dollar exposure across trades
- ✅ No need to calculate ETH amounts manually
- ✅ Works regardless of ETH price

### Option 2: BASE_AMOUNT (Legacy)

Specify amount in the base asset with 4 decimal precision:

```env
BASE_AMOUNT=10000  # 0.001 ETH
```

**When to use:**
- You prefer thinking in ETH terms
- You want fixed ETH amounts regardless of price changes

## Configuration Priority

If **both** are set, `BASE_AMOUNT_IN_USDT` takes priority:

```env
BASE_AMOUNT=10000           # Ignored if BASE_AMOUNT_IN_USDT is set
BASE_AMOUNT_IN_USDT=100     # This will be used
```

To use `BASE_AMOUNT`, leave `BASE_AMOUNT_IN_USDT` empty:

```env
BASE_AMOUNT=10000
BASE_AMOUNT_IN_USDT=        # Empty = use BASE_AMOUNT
```

## Examples

### Testnet Trading (starting with $500)

**Very Conservative** - Allow 100+ test trades:
```env
BASE_URL=https://testnet.zklighter.elliot.ai
BASE_AMOUNT_IN_USDT=1      # $1 per trade
MAX_TRADES=50              # Total: ~$50-100
```

**Safe Testing**:
```env
BASE_URL=https://testnet.zklighter.elliot.ai
BASE_AMOUNT_IN_USDT=5      # $5 per trade
MAX_TRADES=20              # Total: ~$100-200
```

### Mainnet Trading

**Conservative**:
```env
BASE_URL=https://mainnet.zklighter.elliot.ai
BASE_AMOUNT_IN_USDT=50     # $50 per trade
LEVERAGE=5
```

**Moderate**:
```env
BASE_URL=https://mainnet.zklighter.elliot.ai
BASE_AMOUNT_IN_USDT=100    # $100 per trade
LEVERAGE=10
```

**Aggressive**:
```env
BASE_URL=https://mainnet.zklighter.elliot.ai
BASE_AMOUNT_IN_USDT=500    # $500 per trade
LEVERAGE=20
```

## Important Notes

### Delta Neutral Considerations

Remember: The bot opens **two positions** (long + short):
- `BASE_AMOUNT_IN_USDT=100` means $100 for **each** position
- Total exposure: ~$200 per trade pair
- With 10x leverage: Controls ~$2,000 of notional value

### Price Conversion

The bot uses the **mid-price** (average of best bid and ask) for conversion:
```
ETH Amount = BASE_AMOUNT_IN_USDT / ((Best Bid + Best Ask) / 2)
```

This ensures fair pricing and reduces slippage impact.

### Logging

When using USDT sizing, you'll see clear logs:
```
Using BASE_AMOUNT_IN_USDT: $100.00 @ $3543.25 = 0.0282 ETH
```

### Minimum Trade Sizes

Be aware of exchange minimums:
- Lighter DEX may have minimum order sizes
- Too small amounts (e.g., $0.01) might be rejected
- Recommended minimum: $1-5 per trade

## Migration Guide

### Converting Existing BASE_AMOUNT to USDT

If you have:
```env
BASE_AMOUNT=10000  # 0.001 ETH
```

And ETH is at $3,500:
```
0.001 ETH × $3,500 = $3.50
```

Equivalent USDT config:
```env
BASE_AMOUNT_IN_USDT=3.5
```

### Testing Your Configuration

1. Set `MAX_TRADES=1` for a single test
2. Monitor the logs for conversion details
3. Verify the executed trade size matches expectations
4. Adjust as needed

## Troubleshooting

### "Either base_amount or base_amount_in_usdt must be set"

One of them must be non-zero:
```env
# ❌ Both zero/empty
BASE_AMOUNT=0
BASE_AMOUNT_IN_USDT=

# ✅ At least one set
BASE_AMOUNT_IN_USDT=100
```

### Unexpected Trade Sizes

Check your logs for the conversion:
```
Using BASE_AMOUNT_IN_USDT: $100.00 @ $3543.25 = 0.0282 ETH
```

If the price seems wrong, the market might be:
- Illiquid (wide spread)
- Experiencing volatility
- Not showing correct orderbook data

### Legacy Config Not Working

Clear `BASE_AMOUNT_IN_USDT` to use `BASE_AMOUNT`:
```env
BASE_AMOUNT=10000
BASE_AMOUNT_IN_USDT=  # Must be empty or removed
```

---

**Pro Tip:** Start small with USDT sizing ($1-10) to verify everything works correctly before scaling up!

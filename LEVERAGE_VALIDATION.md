# Leverage Limit Validation Feature

## Overview

The bot now automatically validates your configured leverage against Lighter DEX's per-market maximum leverage limits. This prevents configuration errors and ensures compliance with each perpetual futures contract's risk parameters.

## How It Works

### 1. **Market-Specific Leverage Limits**

Each perpetual futures market on Lighter has its own maximum leverage limit, which is determined by the market's `min_initial_margin_fraction` parameter. The relationship is:

```
Maximum Leverage = 1 / Initial Margin Fraction
```

For example:
- If `min_initial_margin_fraction = 500` (representing 5% or 0.05), then max leverage = 20x
- If `min_initial_margin_fraction = 1000` (representing 10% or 0.10), then max leverage = 10x

### 2. **Automatic API Validation**

When the bot starts, it:

1. Loads your configuration from `.env`
2. Queries the Lighter API to fetch market metadata
3. Calculates the maximum allowed leverage for your configured market
4. Compares your `LEVERAGE` setting against the market's maximum
5. **Refuses to start** if your leverage exceeds the limit

### 3. **Configuration**

In your `.env` file:

```bash
# Leverage setting (1-20, depending on market)
LEVERAGE=10

# The bot will validate this against the market's maximum
# If LEVERAGE > market max, the bot will exit with an error
```

## Usage Examples

### Example 1: Valid Configuration

```bash
# .env file
MARKET_INDEX=0
LEVERAGE=10
```

**Bot Output:**
```
✅ Leverage validation passed
   Market 0 max leverage: 20x
   Your configured leverage: 10x
```

### Example 2: Invalid Configuration

```bash
# .env file
MARKET_INDEX=0
LEVERAGE=25  # Exceeds market limit!
```

**Bot Output:**
```
❌ Validation failed: Configured leverage (25x) exceeds the maximum allowed 
   for market 0 (20x). Please set LEVERAGE to 20 or lower in your .env file.
```

## Testing the Feature

Use the provided test script to verify leverage limits for any market:

```powershell
# Activate your virtual environment
.\venv\Scripts\Activate.ps1

# Run the test script
python test_leverage_check.py
```

**Sample Output:**
```
======================================================================
Testing Leverage Limit Check from Lighter API
======================================================================

Configuration loaded:
  Base URL: https://testnet.zklighter.elliot.ai
  Market Index: 0
  Configured Leverage: 10x

Fetching market details from Lighter API...

✅ Successfully fetched market information:
  Market 0 maximum leverage: 20x
  Your configured leverage: 10x

✅ PASS: Your leverage (10x) is within the allowed limit (20x)

Running full validation with API checks...
✅ All validations passed!
```

## API Details

The bot uses the following Lighter API endpoint:

- **Endpoint:** `GET /api/v1/orderBookDetails`
- **Parameter:** `market_id` (your configured `MARKET_INDEX`)
- **Response:** Contains `OrderBookDetail` objects with `min_initial_margin_fraction`

### Code Implementation

The leverage check is implemented in `config.py`:

```python
async def get_market_max_leverage(self) -> int:
    """Fetch maximum leverage allowed for the configured market"""
    configuration = lighter.Configuration(self.base_url)
    api_client = lighter.ApiClient(configuration)
    order_api = lighter.OrderApi(api_client)
    
    order_book_details = await order_api.order_book_details(market_id=self.market_index)
    
    for detail in order_book_details.order_book_details:
        if detail.market_id == self.market_index:
            # min_initial_margin_fraction is in basis points (1/10000)
            min_margin_fraction = detail.min_initial_margin_fraction / 10000.0
            max_leverage = int(1.0 / min_margin_fraction)
            return max_leverage
```

## Benefits

1. **Prevents Configuration Errors:** Catches invalid leverage settings before trading begins
2. **Market-Specific Compliance:** Respects each market's unique risk parameters
3. **Clear Error Messages:** Provides actionable guidance when limits are exceeded
4. **Zero Hardcoding:** No hardcoded leverage limits—always uses live API data

## Migration from Previous Version

**Before (Hardcoded):**
```python
if self.leverage < 1 or self.leverage > 20:
    raise ValueError("leverage must be between 1 and 20")
```

**After (Dynamic):**
```python
max_leverage = await self.get_market_max_leverage()
if self.leverage > max_leverage:
    raise ValueError(f"Configured leverage ({self.leverage}x) exceeds "
                     f"maximum for market {self.market_index} ({max_leverage}x)")
```

## Troubleshooting

### Error: "Failed to fetch market max leverage"

**Possible Causes:**
1. Network connectivity issues
2. Invalid `BASE_URL` in `.env`
3. Invalid `MARKET_INDEX` (market doesn't exist)
4. Lighter API is temporarily unavailable

**Solution:**
- Verify your `BASE_URL` is correct
- Check that `MARKET_INDEX` is valid for your network (testnet/mainnet)
- Try running `test_leverage_check.py` to diagnose the issue

### Error: "Configured leverage exceeds maximum"

**Solution:**
1. Check the error message for the market's max leverage
2. Update `LEVERAGE` in your `.env` file to the maximum or lower
3. Restart the bot

## Related Files

- `config.py` - Contains leverage validation logic
- `delta_neutral_orchestrator.py` - Calls validation on startup
- `test_leverage_check.py` - Test script for leverage validation
- `.env.example` - Updated with leverage documentation

## Notes

- The leverage check runs **once at startup** before any trading begins
- Each market can have different maximum leverage limits
- The validation is **mandatory**—the bot will not start if validation fails
- Testnet and mainnet markets may have different leverage limits

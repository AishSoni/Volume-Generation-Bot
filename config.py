"""
Configuration management for Delta Neutral Bot
"""

import os
from dataclasses import dataclass
from typing import Optional
import lighter
import asyncio


@dataclass
class BotConfig:
    """Configuration for the Delta Neutral Bot"""
    
    # Lighter API Configuration
    base_url: str
    
    # Account 1 (Long positions)
    account1_private_key: str
    account1_index: int
    account1_api_key_index: int
    
    # Account 2 (Short positions)
    account2_private_key: str
    account2_index: int
    account2_api_key_index: int
    
    # Trading Parameters
    market_index: int  # Default/fallback market (kept for backwards compatibility)
    market_whitelist: list[int]  # List of allowed market indices to randomly select from
    base_amount: int  # Base asset amount (e.g., 100000 = 0.01 ETH for 4 decimal precision)
    base_amount_in_usdt: Optional[float]  # Optional: specify trade size in USDT instead of base asset
    max_slippage: float  # Maximum acceptable slippage (e.g., 0.01 = 1%)
    leverage: int  # Trading leverage (1-20) or base leverage for dynamic mode
    use_dynamic_leverage: bool  # If True, randomly select leverage between (max-5) and max for each trade
    leverage_buffer: int  # Buffer below max leverage when using dynamic mode (default: 5)
    margin_mode: int  # 0 = cross margin, 1 = isolated margin
    
    # Bot Behavior
    interval_seconds: int  # Time between NEW trades (deprecated - use min/max_open_delay)
    min_open_delay: int  # Minimum seconds before opening new trade
    max_open_delay: int  # Maximum seconds before opening new trade
    min_close_delay: int  # Minimum seconds before closing position
    max_close_delay: int  # Maximum seconds before closing position
    max_trades: int  # Maximum number of trades (0 = unlimited)
    use_batch_mode: bool  # Whether to use batch transactions
    
    @classmethod
    def from_env(cls) -> 'BotConfig':
        """Create configuration from environment variables"""
        
        # Helper function to get required env var
        def get_required_env(key: str) -> str:
            value = os.getenv(key)
            if value is None:
                raise ValueError(f"Required environment variable {key} is not set")
            return value
        
        # Helper function to get optional env var with default
        def get_optional_env(key: str, default: str) -> str:
            return os.getenv(key, default)
        
        # Helper to ensure private key has 0x prefix
        def ensure_0x_prefix(key: str) -> str:
            return key if key.startswith('0x') else f'0x{key}'
        
        # Helper to parse market whitelist
        def parse_market_whitelist(whitelist_str: str, fallback_market: int) -> list[int]:
            """Parse comma-separated market indices from env var"""
            if not whitelist_str or whitelist_str.strip() == '':
                # If no whitelist provided, use the single market_index
                return [fallback_market]
            
            try:
                markets = [int(m.strip()) for m in whitelist_str.split(',') if m.strip()]
                if not markets:
                    return [fallback_market]
                return markets
            except ValueError as e:
                raise ValueError(f"Invalid MARKET_WHITELIST format. Must be comma-separated integers: {e}")
        
        # Parse market configuration
        market_index = int(get_optional_env('MARKET_INDEX', '0'))
        market_whitelist_str = get_optional_env('MARKET_WHITELIST', '')
        market_whitelist = parse_market_whitelist(market_whitelist_str, market_index)
        
        return cls(
            # API Configuration
            base_url=get_optional_env('BASE_URL', 'https://testnet.zklighter.elliot.ai'),
            
            # Account 1 Configuration
            account1_private_key=ensure_0x_prefix(get_required_env('ACCOUNT1_PRIVATE_KEY')),
            account1_index=int(get_required_env('ACCOUNT1_INDEX')),
            account1_api_key_index=int(get_optional_env('ACCOUNT1_API_KEY_INDEX', '0')),
            
            # Account 2 Configuration
            account2_private_key=ensure_0x_prefix(get_required_env('ACCOUNT2_PRIVATE_KEY')),
            account2_index=int(get_required_env('ACCOUNT2_INDEX')),
            account2_api_key_index=int(get_optional_env('ACCOUNT2_API_KEY_INDEX', '0')),
            
            # Trading Parameters
            market_index=market_index,
            market_whitelist=market_whitelist,
            base_amount=int(get_optional_env('BASE_AMOUNT', '0')),
            base_amount_in_usdt=float(get_optional_env('BASE_AMOUNT_IN_USDT', '0')) or None,
            max_slippage=float(get_optional_env('MAX_SLIPPAGE', '0.02')),  # Default: 2%
            leverage=int(get_optional_env('LEVERAGE', '10')),  # Default: 10x leverage
            use_dynamic_leverage=get_optional_env('USE_DYNAMIC_LEVERAGE', 'false').lower() == 'true',
            leverage_buffer=int(get_optional_env('LEVERAGE_BUFFER', '5')),  # Default: 5x buffer
            margin_mode=int(get_optional_env('MARGIN_MODE', '0')),  # Default: cross margin
            
            # Bot Behavior
            interval_seconds=int(get_optional_env('INTERVAL_SECONDS', '60')),  # Deprecated, kept for backwards compatibility
            min_open_delay=int(get_optional_env('MIN_OPEN_DELAY', '80')),  # Default: 80 seconds
            max_open_delay=int(get_optional_env('MAX_OPEN_DELAY', '120')),  # Default: 120 seconds
            min_close_delay=int(get_optional_env('MIN_CLOSE_DELAY', '30')),  # Default: 30 seconds
            max_close_delay=int(get_optional_env('MAX_CLOSE_DELAY', '50')),  # Default: 50 seconds
            max_trades=int(get_optional_env('MAX_TRADES', '0')),  # Default: unlimited
            use_batch_mode=get_optional_env('USE_BATCH_MODE', 'false').lower() == 'true',
        )
    
    async def get_market_max_leverage(self, market_id: Optional[int] = None) -> int:
        """
        Fetch maximum leverage allowed for a specific market from Lighter API.
        
        Args:
            market_id: Market index to check. If None, uses self.market_index
        
        Returns:
            Maximum leverage as an integer (e.g., 20 for 20x leverage)
        
        Raises:
            Exception if unable to fetch market information
        """
        target_market = market_id if market_id is not None else self.market_index
        
        try:
            configuration = lighter.Configuration(self.base_url)
            api_client = lighter.ApiClient(configuration)
            order_api = lighter.OrderApi(api_client)
            
            # Fetch order book details for the market
            order_book_details = await order_api.order_book_details(market_id=target_market)
            
            await api_client.close()
            
            if order_book_details.order_book_details:
                for detail in order_book_details.order_book_details:
                    if detail.market_id == target_market:
                        # min_initial_margin_fraction is in basis points (1/10000)
                        # For example: 500 means 0.05 (5%), which allows 20x leverage
                        min_margin_fraction = detail.min_initial_margin_fraction / 10000.0
                        max_leverage = int(1.0 / min_margin_fraction)
                        return max_leverage
                
                raise ValueError(f"Market {target_market} not found in order book details")
            else:
                raise ValueError("No order book details returned from API")
                
        except Exception as e:
            raise Exception(f"Failed to fetch market max leverage for market {target_market}: {e}")
    
    async def get_market_info(self, market_id: int) -> dict:
        """
        Fetch market information including symbol name and max leverage.
        
        Args:
            market_id: Market index to fetch info for
            
        Returns:
            Dictionary with market info: {'market_id', 'symbol', 'max_leverage'}
        """
        try:
            configuration = lighter.Configuration(self.base_url)
            api_client = lighter.ApiClient(configuration)
            order_api = lighter.OrderApi(api_client)
            
            order_book_details = await order_api.order_book_details(market_id=market_id)
            await api_client.close()
            
            if order_book_details.order_book_details:
                for detail in order_book_details.order_book_details:
                    if detail.market_id == market_id:
                        min_margin_fraction = detail.min_initial_margin_fraction / 10000.0
                        max_leverage = int(1.0 / min_margin_fraction)
                        return {
                            'market_id': market_id,
                            'symbol': detail.symbol,
                            'max_leverage': max_leverage
                        }
                
                raise ValueError(f"Market {market_id} not found")
            else:
                raise ValueError("No order book details returned from API")
                
        except Exception as e:
            raise Exception(f"Failed to fetch market info for market {market_id}: {e}")
    
    def calculate_dynamic_leverage(self, market_max_leverage: int) -> int:
        """
        Calculate a random leverage value between (max - buffer) and max for a market.
        
        Args:
            market_max_leverage: The maximum leverage allowed for the market
            
        Returns:
            Random leverage value within the dynamic range
        """
        import random
        
        min_leverage = max(1, market_max_leverage - self.leverage_buffer)
        max_leverage = market_max_leverage
        
        # Ensure we have a valid range
        if min_leverage > max_leverage:
            min_leverage = max_leverage
        
        selected_leverage = random.randint(min_leverage, max_leverage)
        return selected_leverage
    
    def validate(self) -> bool:
        """Validate configuration parameters (basic validation without API calls)"""
        if self.max_slippage < 0 or self.max_slippage > 1:
            raise ValueError("max_slippage must be between 0 and 1")
        
        # Validate market whitelist
        if not self.market_whitelist or len(self.market_whitelist) == 0:
            raise ValueError("market_whitelist must contain at least one market")
        
        if any(m < 0 for m in self.market_whitelist):
            raise ValueError("All market indices in whitelist must be non-negative")
        
        # Validate that either base_amount or base_amount_in_usdt is set
        if self.base_amount <= 0 and not self.base_amount_in_usdt:
            raise ValueError("Either base_amount or base_amount_in_usdt must be set")
        
        if self.base_amount_in_usdt and self.base_amount_in_usdt <= 0:
            raise ValueError("base_amount_in_usdt must be positive")
        
        if self.leverage < 1:
            raise ValueError("leverage must be at least 1")
        
        if self.leverage_buffer < 0:
            raise ValueError("leverage_buffer must be non-negative")
        
        if self.margin_mode not in [0, 1]:
            raise ValueError("margin_mode must be 0 (cross) or 1 (isolated)")
        
        if self.interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")
        
        # Validate open delay ranges
        if self.min_open_delay < 0 or self.max_open_delay < 0:
            raise ValueError("open delays must be non-negative")
        
        if self.min_open_delay > self.max_open_delay:
            raise ValueError("min_open_delay must be <= max_open_delay")
        
        # Validate close delay ranges
        if self.min_close_delay < 0 or self.max_close_delay < 0:
            raise ValueError("close delays must be non-negative")
        
        if self.min_close_delay > self.max_close_delay:
            raise ValueError("min_close_delay must be <= max_close_delay")
        
        # CRITICAL VALIDATION: MIN_OPEN_DELAY must be at least 30 seconds larger than MAX_CLOSE_DELAY
        # This ensures new trades are only opened after old positions are closed
        safety_buffer = 30  # seconds
        if self.min_open_delay < (self.max_close_delay + safety_buffer):
            raise ValueError(
                f"MIN_OPEN_DELAY ({self.min_open_delay}s) must be at least {safety_buffer}s larger than "
                f"MAX_CLOSE_DELAY ({self.max_close_delay}s). "
                f"Minimum required: {self.max_close_delay + safety_buffer}s. "
                f"This ensures new trades only open after old positions close."
            )
        
        if self.max_trades < 0:
            raise ValueError("max_trades must be non-negative")
        
        if self.account1_index == self.account2_index:
            raise ValueError("account1_index and account2_index must be different")
        
        return True
    
    async def validate_with_api(self) -> bool:
        """
        Validate configuration parameters including API-based checks.
        This validates leverage against Lighter's limits for ALL whitelisted markets.
        
        Returns:
            True if all validations pass
        
        Raises:
            ValueError if any validation fails
        """
        # First run basic validation
        self.validate()
        
        # Validate leverage for all whitelisted markets
        try:
            if self.use_dynamic_leverage:
                print(f"\nValidating {len(self.market_whitelist)} whitelisted market(s) [Dynamic Leverage Mode]...")
            else:
                print(f"\nValidating {len(self.market_whitelist)} whitelisted market(s)...")
            
            validation_errors = []
            for market_id in self.market_whitelist:
                try:
                    market_info = await self.get_market_info(market_id)
                    max_leverage = market_info['max_leverage']
                    symbol = market_info['symbol']
                    
                    if self.use_dynamic_leverage:
                        # In dynamic mode, check if buffer allows valid range
                        min_dynamic = max(1, max_leverage - self.leverage_buffer)
                        print(f"  ✅ Market {market_id} ({symbol}): Max leverage {max_leverage}x, Dynamic range: {min_dynamic}x-{max_leverage}x")
                    else:
                        # In fixed mode, validate configured leverage
                        if self.leverage > max_leverage:
                            validation_errors.append(
                                f"Market {market_id} ({symbol}): Leverage {self.leverage}x exceeds max {max_leverage}x"
                            )
                        else:
                            print(f"  ✅ Market {market_id} ({symbol}): Max leverage {max_leverage}x")
                except Exception as e:
                    validation_errors.append(f"Market {market_id}: Failed to validate - {e}")
            
            if validation_errors:
                error_msg = "Leverage validation failed for one or more markets:\n" + "\n".join(f"  - {err}" for err in validation_errors)
                raise ValueError(error_msg)
            
            print(f"✅ All whitelisted markets validated successfully")
            return True
            
        except Exception as e:
            raise Exception(f"API validation failed: {e}")
    
    @classmethod
    def from_dict(cls, config_dict: dict) -> 'BotConfig':
        """Create configuration from dictionary"""
        return cls(**config_dict)


# Example configuration for testing (DO NOT USE IN PRODUCTION)
EXAMPLE_CONFIG = {
    'base_url': 'https://testnet.zklighter.elliot.ai',
    'account1_private_key': 'YOUR_ACCOUNT1_PRIVATE_KEY_HERE',
    'account1_index': 1,
    'account1_api_key_index': 0,
    'account2_private_key': 'YOUR_ACCOUNT2_PRIVATE_KEY_HERE',
    'account2_index': 2,
    'account2_api_key_index': 0,
    'market_index': 0,
    'base_amount': 5000,  # 0.5 ETH with 4 decimal precision
    'base_amount_in_usdt': 100.0,  # Alternative: specify $100 USDT per trade (overrides base_amount)
    'max_slippage': 0.02,  # 2% (note: not used in true market orders)
    'leverage': 10,  # 10x leverage
    'margin_mode': 0,  # 0 = cross margin
    'interval_seconds': 60,
    'min_close_delay': 30,
    'max_close_delay': 50,
    'max_trades': 0,  # Unlimited
    'use_batch_mode': False,
}
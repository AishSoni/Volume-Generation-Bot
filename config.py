"""
Configuration Management for Delta Neutral Bot

Handles loading, validation, and management of bot configuration
from environment variables.
"""

import os
from dataclasses import dataclass
from typing import Optional
import lighter


@dataclass
class BotConfig:
    """Bot configuration loaded from environment variables"""
    
    # Lighter API
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
    market_index: int
    market_whitelist: list[int]
    base_amount: int
    base_amount_in_usdt: Optional[float]
    max_slippage: float
    leverage: int
    use_dynamic_leverage: bool
    leverage_buffer: int
    margin_mode: int
    
    # Bot Behavior
    interval_seconds: int  # Deprecated
    min_open_delay: int
    max_open_delay: int
    min_close_delay: int
    max_close_delay: int
    max_trades: int
    use_batch_mode: bool
    
    # Mixed Order Strategy
    limit_order_probability: float
    limit_order_wait_time: int
    limit_order_retry_adjustment: float
    
    @classmethod
    def from_env(cls) -> 'BotConfig':
        """Load configuration from environment variables"""
        
        def get_required_env(key: str) -> str:
            """Get required environment variable or raise error"""
            value = os.getenv(key)
            if value is None:
                raise ValueError(f"Required environment variable {key} is not set")
            return value
        
        def get_optional_env(key: str, default: str) -> str:
            """Get optional environment variable with default"""
            return os.getenv(key, default)
        
        def ensure_0x_prefix(key: str) -> str:
            """Ensure private key has 0x prefix"""
            return key if key.startswith('0x') else f'0x{key}'
        
        def parse_market_whitelist(whitelist_str: str, fallback_market: int) -> list[int]:
            """Parse comma-separated market IDs from string"""
            if not whitelist_str or not whitelist_str.strip():
                return [fallback_market]
            
            try:
                markets = [int(m.strip()) for m in whitelist_str.split(',') if m.strip()]
                return markets if markets else [fallback_market]
            except ValueError as e:
                raise ValueError(f"Invalid MARKET_WHITELIST format: {e}")
        
        market_index = int(get_optional_env('MARKET_INDEX', '0'))
        market_whitelist_str = get_optional_env('MARKET_WHITELIST', '')
        market_whitelist = parse_market_whitelist(market_whitelist_str, market_index)
        
        return cls(
            base_url=get_optional_env('BASE_URL', 'https://testnet.zklighter.elliot.ai'),
            account1_private_key=ensure_0x_prefix(get_required_env('ACCOUNT1_PRIVATE_KEY')),
            account1_index=int(get_required_env('ACCOUNT1_INDEX')),
            account1_api_key_index=int(get_optional_env('ACCOUNT1_API_KEY_INDEX', '0')),
            account2_private_key=ensure_0x_prefix(get_required_env('ACCOUNT2_PRIVATE_KEY')),
            account2_index=int(get_required_env('ACCOUNT2_INDEX')),
            account2_api_key_index=int(get_optional_env('ACCOUNT2_API_KEY_INDEX', '0')),
            market_index=market_index,
            market_whitelist=market_whitelist,
            base_amount=int(get_optional_env('BASE_AMOUNT', '0')),
            base_amount_in_usdt=float(get_optional_env('BASE_AMOUNT_IN_USDT', '0')) or None,
            max_slippage=float(get_optional_env('MAX_SLIPPAGE', '0.02')),
            leverage=int(get_optional_env('LEVERAGE', '10')),
            use_dynamic_leverage=get_optional_env('USE_DYNAMIC_LEVERAGE', 'false').lower() == 'true',
            leverage_buffer=int(get_optional_env('LEVERAGE_BUFFER', '5')),
            margin_mode=int(get_optional_env('MARGIN_MODE', '0')),
            interval_seconds=int(get_optional_env('INTERVAL_SECONDS', '60')),
            min_open_delay=int(get_optional_env('MIN_OPEN_DELAY', '80')),
            max_open_delay=int(get_optional_env('MAX_OPEN_DELAY', '120')),
            min_close_delay=int(get_optional_env('MIN_CLOSE_DELAY', '30')),
            max_close_delay=int(get_optional_env('MAX_CLOSE_DELAY', '50')),
            max_trades=int(get_optional_env('MAX_TRADES', '0')),
            use_batch_mode=get_optional_env('USE_BATCH_MODE', 'false').lower() == 'true',
            limit_order_probability=float(get_optional_env('LIMIT_ORDER_PROBABILITY', '0.8')),
            limit_order_wait_time=int(get_optional_env('LIMIT_ORDER_WAIT_TIME', '90')),
            limit_order_retry_adjustment=float(get_optional_env('LIMIT_ORDER_RETRY_ADJUSTMENT', '0.0002')),
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
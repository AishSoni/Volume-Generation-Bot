"""
Configuration management for Delta Neutral Bot
"""

import os
from dataclasses import dataclass
from typing import Optional


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
    market_index: int
    base_amount: int  # Base asset amount (e.g., 100000 = 0.01 ETH for 4 decimal precision)
    max_slippage: float  # Maximum acceptable slippage (e.g., 0.01 = 1%)
    leverage: int  # Trading leverage (1-20)
    margin_mode: int  # 0 = cross margin, 1 = isolated margin
    
    # Bot Behavior
    interval_seconds: int  # Time between NEW trades
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
            market_index=int(get_optional_env('MARKET_INDEX', '0')),
            base_amount=int(get_optional_env('BASE_AMOUNT', '5000')),  # Default: 0.0005 ETH (~$1 at $2000/ETH)
            max_slippage=float(get_optional_env('MAX_SLIPPAGE', '0.02')),  # Default: 2%
            leverage=int(get_optional_env('LEVERAGE', '10')),  # Default: 10x leverage
            margin_mode=int(get_optional_env('MARGIN_MODE', '0')),  # Default: cross margin
            
            # Bot Behavior
            interval_seconds=int(get_optional_env('INTERVAL_SECONDS', '60')),  # Default: 60 seconds
            min_close_delay=int(get_optional_env('MIN_CLOSE_DELAY', '30')),  # Default: 30 seconds
            max_close_delay=int(get_optional_env('MAX_CLOSE_DELAY', '50')),  # Default: 50 seconds
            max_trades=int(get_optional_env('MAX_TRADES', '0')),  # Default: unlimited
            use_batch_mode=get_optional_env('USE_BATCH_MODE', 'false').lower() == 'true',
        )
    
    def validate(self) -> bool:
        """Validate configuration parameters"""
        if self.max_slippage < 0 or self.max_slippage > 1:
            raise ValueError("max_slippage must be between 0 and 1")
        
        if self.base_amount <= 0:
            raise ValueError("base_amount must be positive")
        
        if self.leverage < 1 or self.leverage > 20:
            raise ValueError("leverage must be between 1 and 20")
        
        if self.margin_mode not in [0, 1]:
            raise ValueError("margin_mode must be 0 (cross) or 1 (isolated)")
        
        if self.interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")
        
        if self.min_close_delay < 0 or self.max_close_delay < 0:
            raise ValueError("close delays must be non-negative")
        
        if self.min_close_delay > self.max_close_delay:
            raise ValueError("min_close_delay must be <= max_close_delay")
        
        if self.max_trades < 0:
            raise ValueError("max_trades must be non-negative")
        
        if self.account1_index == self.account2_index:
            raise ValueError("account1_index and account2_index must be different")
        
        return True
    
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
    'max_slippage': 0.02,  # 2% (note: not used in true market orders)
    'leverage': 10,  # 10x leverage
    'margin_mode': 0,  # 0 = cross margin
    'interval_seconds': 60,
    'min_close_delay': 30,
    'max_close_delay': 50,
    'max_trades': 0,  # Unlimited
    'use_batch_mode': False,
}
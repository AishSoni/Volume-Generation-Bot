"""
Delta Neutral Volume Generation Bot for Lighter DEX

Orchestrates delta-neutral trading by managing two isolated account workers.
Each worker handles a single account to prevent signer conflicts.
"""

import asyncio
import json
import logging
import random
import sys
from datetime import datetime
from typing import Optional, Tuple
from dotenv import load_dotenv
import lighter
from config import BotConfig

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('delta_neutral_bot.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


class DeltaNeutralOrchestrator:
    """
    Orchestrates delta-neutral trading across two isolated account workers.
    
    Manages simultaneous long/short positions, position lifecycle, and
    ensures proper isolation between accounts to prevent signer conflicts.
    """
    
    def __init__(self, config: BotConfig):
        self.config = config
        self.trade_count = 0
        self.success_count = 0
        self.is_running = False
        self.open_positions = []
        self.market_stats = {
            market_id: {'trades': 0, 'successful': 0} 
            for market_id in config.market_whitelist
        }
    
    def select_random_market(self) -> int:
        """Randomly select a market from the whitelist"""
        return random.choice(self.config.market_whitelist)
    
    async def _get_market_precision(self, market_id: int, fallback_price: float) -> int:
        """
        Get the official size_decimals precision for a market from Lighter API.
        
        Args:
            market_id: Market ID to fetch precision for
            fallback_price: Price to use for fallback precision guess
            
        Returns:
            Tuple of (size_decimals, price_decimals)
        """
        try:
            configuration = lighter.Configuration(self.config.base_url)
            api_client = lighter.ApiClient(configuration)
            order_api = lighter.OrderApi(api_client)
            
            order_book_details = await order_api.order_book_details(market_id=market_id)
            await api_client.close()
            
            if order_book_details.order_book_details:
                for detail in order_book_details.order_book_details:
                    if detail.market_id == market_id:
                        return detail.size_decimals, detail.price_decimals
            
            # Fallback if not found
            logger.warning(f"Could not find decimals for market {market_id}, using fallback")
            return self._fallback_precision(fallback_price), 2  # Assume 2 price decimals as fallback
            
        except Exception as e:
            logger.warning(f"Error fetching market precision: {e}, using fallback")
            return self._fallback_precision(fallback_price), 2
    
    def _fallback_precision(self, price: float) -> int:
        """
        Fallback precision calculation based on asset price.
        Used only if API call fails.
        """
        if price >= 10000:
            return 5  # BTC-like assets
        elif price >= 1000:
            return 4  # ETH-like assets
        else:
            return 3  # Most other assets
        
    async def get_current_price(self, market_index: int) -> Optional[Tuple[float, float]]:
        """
        Fetch current best bid and ask prices from the order book.
        
        Args:
            market_index: Market ID to fetch prices for
            
        Returns:
            Tuple of (best_bid, best_ask) or (None, None) if unavailable
        """
        try:
            configuration = lighter.Configuration(self.config.base_url)
            api_client = lighter.ApiClient(configuration)
            order_api = lighter.OrderApi(api_client)
            
            order_book = await order_api.order_book_orders(market_id=market_index, limit=1)
            await api_client.close()
            
            if order_book.asks and order_book.bids:
                best_ask = float(order_book.asks[0].price)
                best_bid = float(order_book.bids[0].price)
                return best_bid, best_ask
            
            logger.warning(f"Order book for market {market_index} has no bids or asks")
            return None, None
                
        except Exception as e:
            logger.error(f"Error fetching price for market {market_index}: {e}")
            return None, None
    
    async def run_worker_command(self, account_config: dict, command_config: dict) -> dict:
        """
        Execute a command in an isolated worker process.
        
        Args:
            account_config: Account credentials and settings
            command_config: Command type and parameters
            
        Returns:
            Dictionary with 'success' status and result or error message
        """
        try:
            full_config = {'account': account_config, **command_config}
            
            # Launch isolated worker process
            process = await asyncio.create_subprocess_exec(
                sys.executable,
                'account_worker.py',
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Send configuration and get result
            config_json = json.dumps(full_config)
            stdout, stderr = await process.communicate(input=config_json.encode())
            
            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else 'Unknown error'
                return {'success': False, 'error': f'Worker failed: {error_msg}'}
            
            return json.loads(stdout.decode())
            
        except Exception as e:
            return {'success': False, 'error': f'Worker exception: {str(e)}'}
    
    async def update_leverage_both_accounts(
        self, 
        leverage: Optional[int] = None, 
        market_index: Optional[int] = None
    ):
        """
        Update leverage on both accounts with the same value.
        
        Args:
            leverage: Leverage to set (uses config.leverage if None)
            market_index: Market ID (uses config.market_index if None)
        """
        actual_leverage = leverage if leverage is not None else self.config.leverage
        actual_market = market_index if market_index is not None else self.config.market_index
        
        margin_mode = 'cross' if self.config.margin_mode == 0 else 'isolated'
        logger.info(f"Setting leverage: {actual_leverage}x ({margin_mode} margin)")
        
        account1_config = {
            'base_url': self.config.base_url,
            'private_key': self.config.account1_private_key,
            'account_index': self.config.account1_index,
            'api_key_index': self.config.account1_api_key_index,
        }
        
        account2_config = {
            'base_url': self.config.base_url,
            'private_key': self.config.account2_private_key,
            'account_index': self.config.account2_index,
            'api_key_index': self.config.account2_api_key_index,
        }
        
        leverage_command = {
            'command': 'update_leverage',
            'leverage': {
                'market_index': actual_market,
                'leverage': actual_leverage,
                'margin_mode': self.config.margin_mode
            }
        }
        
        # Update leverage for both accounts in parallel
        await asyncio.gather(
            self.run_worker_command(account1_config, leverage_command),
            self.run_worker_command(account2_config, leverage_command),
            return_exceptions=True
        )
        
        logger.info("✅ Leverage updated on both accounts")
        return True
    
    async def update_leverage_for_accounts(
        self, 
        leverage_account1: int, 
        leverage_account2: int, 
        market_index: int
    ):
        """
        Update leverage independently for each account (asymmetric leverage).
        
        Args:
            leverage_account1: Leverage for account 1 (long)
            leverage_account2: Leverage for account 2 (short)
            market_index: Market ID
        """
        logger.info(f"Setting asymmetric leverage for market {market_index}:")
        logger.info(f"  Long: {leverage_account1}x | Short: {leverage_account2}x")
        
        account1_config = {
            'base_url': self.config.base_url,
            'private_key': self.config.account1_private_key,
            'account_index': self.config.account1_index,
            'api_key_index': self.config.account1_api_key_index,
        }
        
        account2_config = {
            'base_url': self.config.base_url,
            'private_key': self.config.account2_private_key,
            'account_index': self.config.account2_index,
            'api_key_index': self.config.account2_api_key_index,
        }
        
        leverage_command_account1 = {
            'command': 'update_leverage',
            'leverage': {
                'market_index': market_index,
                'leverage': leverage_account1,
                'margin_mode': self.config.margin_mode
            }
        }
        
        leverage_command_account2 = {
            'command': 'update_leverage',
            'leverage': {
                'market_index': market_index,
                'leverage': leverage_account2,
                'margin_mode': self.config.margin_mode
            }
        }
        
        # Update leverage for both accounts in parallel with different values
        results = await asyncio.gather(
            self.run_worker_command(account1_config, leverage_command_account1),
            self.run_worker_command(account2_config, leverage_command_account2),
            return_exceptions=True
        )
        
        logger.info("✅ Leverage updated on both accounts")
        return True
    
    async def execute_delta_neutral_trade(self) -> Tuple[bool, str]:
        """Execute simultaneous long and short orders using mixed order strategy (80% limit, 20% market)"""
        try:
            # Randomly select a market from the whitelist
            selected_market = self.select_random_market()
            
            # Decide order type for this trade pair (same for both long and short)
            use_limit_order = random.random() < self.config.limit_order_probability
            
            # Get market info and determine leverage for this trade
            try:
                market_info = await self.config.get_market_info(selected_market)
                market_symbol = market_info['symbol']
                market_max_leverage = market_info['max_leverage']
                
                # Calculate leverage for this trade
                if self.config.use_dynamic_leverage:
                    # Select different leverage for each account
                    leverage_long = self.config.calculate_dynamic_leverage(market_max_leverage)
                    leverage_short = self.config.calculate_dynamic_leverage(market_max_leverage)
                    logger.info(f"📊 Selected market: {market_symbol} (ID: {selected_market})")
                    logger.info(f"   🎲 Dynamic leverage - Long: {leverage_long}x | Short: {leverage_short}x (max: {market_max_leverage}x)")
                else:
                    leverage_long = self.config.leverage
                    leverage_short = self.config.leverage
                    logger.info(f"📊 Selected market: {market_symbol} (ID: {selected_market})")
                    
            except Exception as e:
                logger.warning(f"Could not fetch market info: {e}")
                market_symbol = f"Market {selected_market}"
                leverage_long = self.config.leverage
                leverage_short = self.config.leverage
                logger.info(f"📊 Selected market: {market_symbol} (ID: {selected_market})")
            
            # Log order type
            order_type_emoji = "📝" if use_limit_order else "⚡"
            order_type_name = "LIMIT" if use_limit_order else "MARKET"
            logger.info(f"{order_type_emoji} Order Type: {order_type_name} ({self.config.limit_order_probability*100:.0f}% limit probability)")
            
            # Update leverage for each account independently (if dynamic mode)
            if self.config.use_dynamic_leverage:
                await self.update_leverage_for_accounts(
                    leverage_account1=leverage_long,
                    leverage_account2=leverage_short,
                    market_index=selected_market
                )
            
            # Get current bid and ask for the selected market
            best_bid, best_ask = await self.get_current_price(selected_market)
            if not best_bid or not best_ask:
                return False, f"Failed to get current price for {market_symbol}"

            # --- PRE-TRADE SAFEGUARD: Check Bid-Ask Spread ---
            spread = best_ask - best_bid
            spread_percentage = (spread / best_ask) * 100
            max_spread_percentage = 0.1  # Allow up to 0.1% spread

            if spread_percentage > max_spread_percentage:
                logger.warning(f"Spread ({spread_percentage:.4f}%) exceeds max ({max_spread_percentage}%) - skipping trade")
                return False, f"Spread too wide for {market_symbol}"
            
            # Calculate base_amount from USDT margin target
            if self.config.base_amount_in_usdt:
                mid_price = (best_bid + best_ask) / 2
                
                # Calculate effective leverage for this trade
                effective_leverage_long = (
                    leverage_long if self.config.use_dynamic_leverage 
                    else self.config.leverage
                )
                effective_leverage_short = (
                    leverage_short if self.config.use_dynamic_leverage 
                    else self.config.leverage
                )
                avg_leverage = (effective_leverage_long + effective_leverage_short) / 2
                
                # Fetch official precision from Lighter API
                precision_decimals, price_decimals = await self._get_market_precision(selected_market, mid_price)
                precision_multiplier = 10 ** precision_decimals
                price_multiplier = 10 ** price_decimals
                
                # Calculate base_amount from margin target
                # Formula: base_amount = (margin * leverage / price) * precision_multiplier
                target_notional = self.config.base_amount_in_usdt * avg_leverage
                asset_amount = target_notional / mid_price
                base_amount = max(1, round(asset_amount * precision_multiplier))
                
                # Calculate actual values for logging
                base_amount_decimal = base_amount / precision_multiplier
                actual_notional_usd = base_amount_decimal * mid_price
                margin_long = actual_notional_usd / effective_leverage_long
                margin_short = actual_notional_usd / effective_leverage_short
                
                logger.info(f"Using BASE_AMOUNT_IN_USDT: ${self.config.base_amount_in_usdt:.2f} (target margin)")
                logger.info(f"  Asset: {market_symbol.split('-')[0]}, Price: ${mid_price:.2f}")
                logger.info(f"  Precision: {precision_decimals} decimals (multiplier: {precision_multiplier})")
                logger.info(f"  Average leverage: {avg_leverage:.1f}x")
                logger.info(f"  Target notional: ${target_notional:.2f}")
                logger.info(f"  Asset amount: {base_amount_decimal:.{precision_decimals}f}")
                logger.info(f"  Actual notional: ${actual_notional_usd:.2f}")
                logger.info(f"  Long: ${actual_notional_usd:.2f} notional / {effective_leverage_long}x = ${margin_long:.2f} margin")
                logger.info(f"  Short: ${actual_notional_usd:.2f} notional / {effective_leverage_short}x = ${margin_short:.2f} margin")
                # Store precision for later display
                display_precision = precision_decimals
                display_multiplier = precision_multiplier
            else:
                base_amount = self.config.base_amount
                # Default to 4 decimals if not using USDT sizing
                display_precision = 4
                display_multiplier = 10000
            
            logger.info(f"Executing delta neutral trade on {market_symbol}:")
            logger.info(f"  Base amount: {base_amount / display_multiplier:.{display_precision}f} {market_symbol.split('-')[0]}")
            logger.info(f"  Best Bid: ${best_bid:.2f}, Best Ask: ${best_ask:.2f}")
            logger.info(f"  Spread: ${spread:.2f} ({spread_percentage:.3f}%)")
            logger.info(f"  Long leverage: {leverage_long}x | Short leverage: {leverage_short}x")
            
            # Prepare account configurations
            account1_config = {
                'base_url': self.config.base_url,
                'private_key': self.config.account1_private_key,
                'account_index': self.config.account1_index,
                'api_key_index': self.config.account1_api_key_index,
            }
            
            account2_config = {
                'base_url': self.config.base_url,
                'private_key': self.config.account2_private_key,
                'account_index': self.config.account2_index,
                'api_key_index': self.config.account2_api_key_index,
            }
            
            # Prepare order commands based on order type
            timestamp_ms = int(datetime.now().timestamp() * 1000)
            
            if use_limit_order:
                # Use limit orders INSIDE the spread to avoid crossing (post-only requirement)
                # Long (buy): Must be BELOW best ask
                # Short (sell): Must be ABOVE best bid
                spread = best_ask - best_bid
                
                # Place orders slightly inside the spread (90% towards mid from edges)
                # This ensures we don't cross while still being competitive
                spread_position = 0.4  # 40% into spread from each side
                
                long_limit_price_float = best_bid + (spread * spread_position)
                short_limit_price_float = best_ask - (spread * spread_position)
                
                # Get price decimals for proper integer conversion
                _, price_decimals = await self._get_market_precision(selected_market, long_limit_price_float)
                price_multiplier = 10 ** price_decimals
                
                # Convert float prices to integers as required by SDK
                long_limit_price = int(long_limit_price_float * price_multiplier)
                short_limit_price = int(short_limit_price_float * price_multiplier)
                
                logger.info(f"  📝 Placing LIMIT orders inside spread:")
                logger.info(f"     Long (buy) at ${long_limit_price_float:.4f} (int: {long_limit_price}) [Below ask: ${best_ask:.4f}]")
                logger.info(f"     Short (sell) at ${short_limit_price_float:.4f} (int: {short_limit_price}) [Above bid: ${best_bid:.4f}]")
                
                long_command = {
                    'command': 'execute_limit_order',
                    'order': {
                        'market_index': selected_market,
                        'base_amount': base_amount,
                        'is_ask': False,  # Buy = Long
                        'client_order_index': timestamp_ms % 1000000,
                        'limit_price': long_limit_price
                    }
                }
                
                short_command = {
                    'command': 'execute_limit_order',
                    'order': {
                        'market_index': selected_market,
                        'base_amount': base_amount,
                        'is_ask': True,  # Sell = Short
                        'client_order_index': (timestamp_ms + 1) % 1000000,
                        'limit_price': short_limit_price
                    }
                }
            else:
                # Use market orders with worst-case prices
                long_execution_price = 999999999
                short_execution_price = 1
                
                logger.info(f"  ⚡ Placing MARKET orders")

                long_command = {
                    'command': 'execute_true_market_order',
                    'order': {
                        'market_index': selected_market,
                        'base_amount': base_amount,
                        'is_ask': False,  # Buy = Long
                        'client_order_index': timestamp_ms % 1000000,
                        'execution_price': long_execution_price
                    }
                }
                
                short_command = {
                    'command': 'execute_true_market_order',
                    'order': {
                        'market_index': selected_market,
                        'base_amount': base_amount,
                        'is_ask': True,  # Sell = Short
                        'client_order_index': (timestamp_ms + 1) % 1000000,
                        'execution_price': short_execution_price
                    }
                }
            
            # Execute both orders in parallel using isolated workers
            results = await asyncio.gather(
                self.run_worker_command(account1_config, long_command),
                self.run_worker_command(account2_config, short_command),
                return_exceptions=True
            )
            
            long_result, short_result = results
            
            # Check results
            long_success = isinstance(long_result, dict) and long_result.get('success', False)
            short_success = isinstance(short_result, dict) and short_result.get('success', False)
            
            # Log any errors from limit order placement
            if use_limit_order:
                if not long_success:
                    error_msg = long_result.get('error', 'Unknown error') if isinstance(long_result, dict) else str(long_result)
                    logger.error(f"❌ Long limit order placement failed: {error_msg}")
                if not short_success:
                    error_msg = short_result.get('error', 'Unknown error') if isinstance(short_result, dict) else str(short_result)
                    logger.error(f"❌ Short limit order placement failed: {error_msg}")
            
            # If using limit orders, wait for fill confirmation
            if use_limit_order and long_success and short_success:
                logger.info(f"✅ Limit orders placed successfully")
                logger.info(f"   Waiting {self.config.limit_order_wait_time}s for orders to fill...")
                
                # Extract order IDs
                long_order_id = long_result.get('order_id')
                short_order_id = short_result.get('order_id')
                
                # Wait for specified time
                await asyncio.sleep(self.config.limit_order_wait_time)
                
                # Check fill status
                fill_check_long = await self.run_worker_command(account1_config, {
                    'command': 'get_order_status',
                    'order': {
                        'market_index': selected_market,
                        'order_id': long_order_id
                    }
                })
                
                fill_check_short = await self.run_worker_command(account2_config, {
                    'command': 'get_order_status',
                    'order': {
                        'market_index': selected_market,
                        'order_id': short_order_id
                    }
                })
                
                long_filled = fill_check_long.get('filled', False)
                short_filled = fill_check_short.get('filled', False)
                
                # CASE 1: Both orders filled - Success!
                if long_filled and short_filled:
                    logger.info(f"✅ Both limit orders filled successfully!")
                    # long_success and short_success already True, will proceed to create positions
                
                # CASE 2: Both orders unfilled - Retry up to max_retries times with adjusted prices
                elif not long_filled and not short_filled:
                    logger.warning(f"⏱️  Both orders unfilled after {self.config.limit_order_wait_time}s")
                    
                    # Cancel both unfilled orders
                    await self.run_worker_command(account1_config, {
                        'command': 'cancel_order',
                        'order': {'market_index': selected_market, 'order_id': long_order_id}
                    })
                    await self.run_worker_command(account2_config, {
                        'command': 'cancel_order',
                        'order': {'market_index': selected_market, 'order_id': short_order_id}
                    })
                    
                    # Retry loop
                    retry_success = False
                    for retry_attempt in range(1, self.config.limit_order_max_retries + 1):
                        logger.info(f"🔄 Retry attempt {retry_attempt}/{self.config.limit_order_max_retries} with adjusted prices...")
                        
                        # Get fresh prices
                        best_bid, best_ask = await self.get_current_price(selected_market)
                        if not best_bid or not best_ask:
                            return False, f"Failed to get price for retry"
                        
                        # Get price decimals for integer conversion
                        _, price_decimals = await self._get_market_precision(selected_market, best_ask)
                        price_multiplier = 10 ** price_decimals
                        
                        # Adjust prices to be more aggressive but still inside spread
                        # Move closer to mid-price for faster fill while maintaining post-only
                        spread = best_ask - best_bid
                        spread_adjustment_pct = self.config.limit_order_retry_adjustment
                        
                        # Each retry moves progressively closer to mid (40% → 45% → 47.5% etc.)
                        # Formula: 0.4 + (spread_adjustment_pct * 0.25 * retry_attempt)
                        retry_position = 0.4 + (spread_adjustment_pct * 0.25 * retry_attempt)
                        retry_long_price_float = best_bid + (spread * retry_position)
                        retry_short_price_float = best_ask - (spread * retry_position)
                        
                        # Ensure we never cross the book
                        retry_long_price_float = min(retry_long_price_float, best_ask - (spread * 0.01))  # At least 1% below ask
                        retry_short_price_float = max(retry_short_price_float, best_bid + (spread * 0.01))  # At least 1% above bid
                        
                        retry_long_price = int(retry_long_price_float * price_multiplier)
                        retry_short_price = int(retry_short_price_float * price_multiplier)
                        
                        logger.info(f"   Market: Bid ${best_bid:.2f}, Ask ${best_ask:.2f}")
                        logger.info(f"   Retry prices: Long ${retry_long_price_float:.4f}, Short ${retry_short_price_float:.4f}")
                        
                        # Generate unique order IDs for this retry attempt
                        retry_long_order_id = (timestamp_ms + 10 + (retry_attempt * 2)) % 1000000
                        retry_short_order_id = (timestamp_ms + 11 + (retry_attempt * 2)) % 1000000
                        
                        # Place retry orders
                        retry_long_cmd = {
                            'command': 'execute_limit_order',
                            'order': {
                                'market_index': selected_market,
                                'base_amount': base_amount,
                                'is_ask': False,
                                'client_order_index': retry_long_order_id,
                                'limit_price': retry_long_price
                            }
                        }
                        retry_short_cmd = {
                            'command': 'execute_limit_order',
                            'order': {
                                'market_index': selected_market,
                                'base_amount': base_amount,
                                'is_ask': True,
                                'client_order_index': retry_short_order_id,
                                'limit_price': retry_short_price
                            }
                        }
                        
                        retry_results = await asyncio.gather(
                            self.run_worker_command(account1_config, retry_long_cmd),
                            self.run_worker_command(account2_config, retry_short_cmd),
                            return_exceptions=True
                        )
                        
                        # Check if retry orders placed successfully
                        if any(isinstance(r, Exception) or not r.get('success', False) for r in retry_results):
                            logger.error(f"❌ Retry {retry_attempt} order placement failed - skipping trade")
                            return False, f"Retry orders failed to place for {market_symbol}"
                        
                        # Wait for retry orders to fill (same wait time for consistency)
                        logger.info(f"   Waiting {self.config.limit_order_wait_time}s for retry orders to fill...")
                        await asyncio.sleep(self.config.limit_order_wait_time)
                        
                        # Check if retry orders filled
                        retry_long_check = await self.run_worker_command(account1_config, {
                            'command': 'get_order_status',
                            'order': {'market_index': selected_market, 'order_id': retry_long_order_id}
                        })
                        retry_short_check = await self.run_worker_command(account2_config, {
                            'command': 'get_order_status',
                            'order': {'market_index': selected_market, 'order_id': retry_short_order_id}
                        })
                        
                        retry_long_filled = retry_long_check.get('filled', False)
                        retry_short_filled = retry_short_check.get('filled', False)
                        
                        # CASE 2a: Both retry orders filled - Success!
                        if retry_long_filled and retry_short_filled:
                            logger.info(f"✅ Both retry orders filled on attempt {retry_attempt}!")
                            retry_success = True
                            break
                        
                        # CASE 2b: Both retry orders still unfilled - Continue to next retry or give up
                        elif not retry_long_filled and not retry_short_filled:
                            logger.warning(f"⚠️  Both retry orders unfilled on attempt {retry_attempt}")
                            # Cancel these retry orders before next attempt
                            await self.run_worker_command(account1_config, {
                                'command': 'cancel_order',
                                'order': {'market_index': selected_market, 'order_id': retry_long_order_id}
                            })
                            await self.run_worker_command(account2_config, {
                                'command': 'cancel_order',
                                'order': {'market_index': selected_market, 'order_id': retry_short_order_id}
                            })
                            # Continue to next retry attempt (or give up if this was the last)
                        
                        # CASE 2c: One retry filled, other not - Close filled position and give up
                        else:
                            logger.warning(f"⚠️  Asymmetric fill after retry {retry_attempt} (Long: {retry_long_filled}, Short: {retry_short_filled})")
                            
                            if retry_long_filled:
                                logger.warning(f"⚠️  Closing filled long position...")
                                await self.run_worker_command(account2_config, {
                                    'command': 'cancel_order',
                                    'order': {'market_index': selected_market, 'order_id': retry_short_order_id}
                                })
                                await self.run_worker_command(account1_config, {
                                    'command': 'execute_true_market_order',
                                    'order': {
                                        'market_index': selected_market,
                                        'base_amount': base_amount,
                                        'is_ask': True,
                                        'client_order_index': (timestamp_ms + 20 + retry_attempt) % 1000000,
                                        'execution_price': 1,
                                        'reduce_only': True
                                    }
                                })
                            else:
                                logger.warning(f"⚠️  Closing filled short position...")
                                await self.run_worker_command(account1_config, {
                                    'command': 'cancel_order',
                                    'order': {'market_index': selected_market, 'order_id': retry_long_order_id}
                                })
                                await self.run_worker_command(account2_config, {
                                    'command': 'execute_true_market_order',
                                    'order': {
                                        'market_index': selected_market,
                                        'base_amount': base_amount,
                                        'is_ask': False,
                                        'client_order_index': (timestamp_ms + 21 + retry_attempt) % 1000000,
                                        'execution_price': 999999999,
                                        'reduce_only': True
                                    }
                                })
                            
                            return False, f"Asymmetric fill after retry {retry_attempt} for {market_symbol}"
                    
                    # After all retries
                    if not retry_success:
                        logger.warning(f"⚠️  All {self.config.limit_order_max_retries} retry attempts exhausted - giving up on this trade")
                        return False, f"Limit orders unfilled after {self.config.limit_order_max_retries} retries for {market_symbol}"
                    
                    # If we got here with retry_success=True, keep long_success and short_success True
                
                # CASE 3: One side filled, other not - Close filled IMMEDIATELY then retry both
                else:
                    logger.warning(f"⚠️  Asymmetric fill detected (Long: {long_filled}, Short: {short_filled})")
                    
                    # Determine which side filled and close it immediately
                    if long_filled:
                        logger.warning(f"⚠️  Long filled but short unfilled - closing long position immediately")
                        
                        # Cancel unfilled short order
                        await self.run_worker_command(account2_config, {
                            'command': 'cancel_order',
                            'order': {'market_index': selected_market, 'order_id': short_order_id}
                        })
                        
                        # Close filled long position with market order
                        close_result = await self.run_worker_command(account1_config, {
                            'command': 'execute_true_market_order',
                            'order': {
                                'market_index': selected_market,
                                'base_amount': base_amount,
                                'is_ask': True,  # Sell to close long
                                'client_order_index': (timestamp_ms + 20) % 1000000,
                                'execution_price': 1,
                                'reduce_only': True
                            }
                        })
                        
                        if not close_result.get('success'):
                            logger.error(f"❌ CRITICAL: Failed to close long position: {close_result.get('error')}")
                        else:
                            logger.info(f"   ✅ Long position closed")
                    
                    else:  # short filled, long not
                        logger.warning(f"⚠️  Short filled but long unfilled - closing short position immediately")
                        
                        # Cancel unfilled long order
                        await self.run_worker_command(account1_config, {
                            'command': 'cancel_order',
                            'order': {'market_index': selected_market, 'order_id': long_order_id}
                        })
                        
                        # Close filled short position with market order
                        close_result = await self.run_worker_command(account2_config, {
                            'command': 'execute_true_market_order',
                            'order': {
                                'market_index': selected_market,
                                'base_amount': base_amount,
                                'is_ask': False,  # Buy to close short
                                'client_order_index': (timestamp_ms + 21) % 1000000,
                                'execution_price': 999999999,
                                'reduce_only': True
                            }
                        })
                        
                        if not close_result.get('success'):
                            logger.error(f"❌ CRITICAL: Failed to close short position: {close_result.get('error')}")
                        else:
                            logger.info(f"   ✅ Short position closed")
                    
                    # Now retry BOTH orders with adjusted prices (fresh start)
                    logger.info(f"🔄 Retrying both orders with adjusted prices after closing asymmetric position...")
                    
                    # Get fresh prices
                    best_bid, best_ask = await self.get_current_price(selected_market)
                    if not best_bid or not best_ask:
                        return False, f"Failed to get price for retry after asymmetric close"
                    
                    # Get price decimals
                    _, price_decimals = await self._get_market_precision(selected_market, best_ask)
                    price_multiplier = 10 ** price_decimals
                    
                    # Adjust prices to be more aggressive but still inside spread
                    spread = best_ask - best_bid
                    spread_adjustment_pct = self.config.limit_order_retry_adjustment
                    
                    # Retry: Move deeper into spread for faster fill
                    retry_long_price_float = best_bid + (spread * (0.4 + spread_adjustment_pct * 0.25))
                    retry_short_price_float = best_ask - (spread * (0.4 + spread_adjustment_pct * 0.25))
                    
                    # Ensure we never cross the book
                    retry_long_price_float = min(retry_long_price_float, best_ask - (spread * 0.01))
                    retry_short_price_float = max(retry_short_price_float, best_bid + (spread * 0.01))
                    
                    retry_long_price = int(retry_long_price_float * price_multiplier)
                    retry_short_price = int(retry_short_price_float * price_multiplier)
                    
                    logger.info(f"   Market: Bid ${best_bid:.2f}, Ask ${best_ask:.2f}")
                    logger.info(f"   Retry prices: Long ${retry_long_price_float:.4f}, Short ${retry_short_price_float:.4f}")
                    
                    # Place both retry orders
                    retry_long_cmd = {
                        'command': 'execute_limit_order',
                        'order': {
                            'market_index': selected_market,
                            'base_amount': base_amount,
                            'is_ask': False,
                            'client_order_index': (timestamp_ms + 30) % 1000000,
                            'limit_price': retry_long_price
                        }
                    }
                    retry_short_cmd = {
                        'command': 'execute_limit_order',
                        'order': {
                            'market_index': selected_market,
                            'base_amount': base_amount,
                            'is_ask': True,
                            'client_order_index': (timestamp_ms + 31) % 1000000,
                            'limit_price': retry_short_price
                        }
                    }
                    
                    retry_results = await asyncio.gather(
                        self.run_worker_command(account1_config, retry_long_cmd),
                        self.run_worker_command(account2_config, retry_short_cmd),
                        return_exceptions=True
                    )
                    
                    # Check placement success
                    if any(isinstance(r, Exception) or not r.get('success', False) for r in retry_results):
                        logger.error(f"❌ Retry order placement failed after asymmetric close")
                        return False, f"Retry failed after asymmetric close for {market_symbol}"
                    
                    # Wait for retry orders
                    retry_wait_time = self.config.limit_order_wait_time // 2
                    logger.info(f"   Waiting {retry_wait_time}s for retry orders to fill...")
                    await asyncio.sleep(retry_wait_time)
                    
                    # Check retry fills
                    retry_long_check = await self.run_worker_command(account1_config, {
                        'command': 'get_order_status',
                        'order': {'market_index': selected_market, 'order_id': (timestamp_ms + 30) % 1000000}
                    })
                    retry_short_check = await self.run_worker_command(account2_config, {
                        'command': 'get_order_status',
                        'order': {'market_index': selected_market, 'order_id': (timestamp_ms + 31) % 1000000}
                    })
                    
                    retry_long_filled = retry_long_check.get('filled', False)
                    retry_short_filled = retry_short_check.get('filled', False)
                    
                    # If both filled now - Success!
                    if retry_long_filled and retry_short_filled:
                        logger.info(f"✅ Both retry orders filled after asymmetric close!")
                        # Keep long_success and short_success True
                    else:
                        # Give up - cancel unfilled orders and close any newly filled positions
                        logger.warning(f"⚠️  Retry incomplete after asymmetric close (Long: {retry_long_filled}, Short: {retry_short_filled})")
                        
                        if not retry_long_filled:
                            await self.run_worker_command(account1_config, {
                                'command': 'cancel_order',
                                'order': {'market_index': selected_market, 'order_id': (timestamp_ms + 30) % 1000000}
                            })
                        
                        if not retry_short_filled:
                            await self.run_worker_command(account2_config, {
                                'command': 'cancel_order',
                                'order': {'market_index': selected_market, 'order_id': (timestamp_ms + 31) % 1000000}
                            })
                        
                        # Close any new filled positions from retry
                        if retry_long_filled:
                            await self.run_worker_command(account1_config, {
                                'command': 'execute_true_market_order',
                                'order': {
                                    'market_index': selected_market,
                                    'base_amount': base_amount,
                                    'is_ask': True,
                                    'client_order_index': (timestamp_ms + 40) % 1000000,
                                    'execution_price': 1,
                                    'reduce_only': True
                                }
                            })
                        
                        if retry_short_filled:
                            await self.run_worker_command(account2_config, {
                                'command': 'execute_true_market_order',
                                'order': {
                                    'market_index': selected_market,
                                    'base_amount': base_amount,
                                    'is_ask': False,
                                    'client_order_index': (timestamp_ms + 41) % 1000000,
                                    'execution_price': 999999999,
                                    'reduce_only': True
                                }
                            })
                        
                        return False, f"Failed to establish delta-neutral position after retry for {market_symbol}"
            
            # For market orders, log immediately
            if not use_limit_order:
                if long_success:
                    logger.info(f"✅ Long order (Account 1): TX {long_result.get('tx_hash', 'N/A')[:16]}...")
                else:
                    logger.error(f"❌ Long order failed: {long_result.get('error', 'Unknown error') if isinstance(long_result, dict) else str(long_result)}")
                
                if short_success:
                    logger.info(f"✅ Short order (Account 2): TX {short_result.get('tx_hash', 'N/A')[:16]}...")
                else:
                    logger.error(f"❌ Short order failed: {short_result.get('error', 'Unknown error') if isinstance(short_result, dict) else str(short_result)}")
            
            # Both must succeed for delta neutral
            if long_success and short_success:
                # Update market stats
                self.market_stats[selected_market]['trades'] += 1
                self.market_stats[selected_market]['successful'] += 1
                
                # Schedule position closing
                close_delay = random.randint(self.config.min_close_delay, self.config.max_close_delay)
                position_info = {
                    'market_index': selected_market,
                    'market_symbol': market_symbol,
                    'base_amount': base_amount,
                    'close_time': asyncio.get_event_loop().time() + close_delay,
                    'close_delay': close_delay,
                    'trade_number': self.trade_count
                }
                self.open_positions.append(position_info)
                
                logger.info(f"✅ Delta neutral trade executed successfully on {market_symbol}")
                logger.info(f"📅 Position will close in {close_delay} seconds")
                return True, "Success"
            else:
                # Update market stats for failed trade
                self.market_stats[selected_market]['trades'] += 1
                return False, f"One or both orders failed for {market_symbol}"
                
        except Exception as e:
            logger.error(f"Error executing trade: {e}")
            return False, str(e)
    
    async def close_positions_task(self):
        """Background task to close positions when their time comes"""
        while self.is_running:
            try:
                current_time = asyncio.get_event_loop().time()
                positions_to_close = []
                remaining_positions = []
                
                for pos in self.open_positions:
                    if current_time >= pos['close_time']:
                        positions_to_close.append(pos)
                    else:
                        remaining_positions.append(pos)
                
                # Close positions that are ready
                if positions_to_close:
                    for pos in positions_to_close:
                        market_symbol = pos.get('market_symbol', f'Market {pos["market_index"]}')
                        logger.info(f"\n{'='*60}")
                        logger.info(f"Closing positions from Trade #{pos['trade_number']} - {market_symbol}")
                        logger.info(f"{'='*60}")
                        await self.close_position_pair(
                            pos['market_index'],
                            pos['base_amount'],
                            market_symbol
                        )
                    
                    # Only update the list after closing is complete
                    self.open_positions = remaining_positions
                
                await asyncio.sleep(1)  # Check every second
                
            except Exception as e:
                logger.error(f"Error in close positions task: {e}")
                await asyncio.sleep(5)
    
    async def close_position_pair(self, market_index: int, base_amount: int, market_symbol: str = None):
        """Close both long and short positions for a specific market"""
        try:
            if market_symbol is None:
                market_symbol = f"Market {market_index}"
            # Prepare account configurations
            account1_config = {
                'base_url': self.config.base_url,
                'private_key': self.config.account1_private_key,
                'account_index': self.config.account1_index,
                'api_key_index': self.config.account1_api_key_index,
            }
            
            account2_config = {
                'base_url': self.config.base_url,
                'private_key': self.config.account2_private_key,
                'account_index': self.config.account2_index,
                'api_key_index': self.config.account2_api_key_index,
            }

            # To close positions, we use true market orders with wide boundaries
            close_long_execution_price = 1  # Sell to close long (accept any price)
            close_short_execution_price = 999999999  # Buy to close short (accept any price)

            # Close commands
            close_long_command = {
                'command': 'execute_true_market_order',
                'order': {
                    'market_index': market_index,
                    'base_amount': base_amount,
                    'is_ask': True,  # Sell to close long
                    'client_order_index': int(datetime.now().timestamp() * 1000 + 2) % 1000000,
                    'reduce_only': True,
                    'execution_price': close_long_execution_price
                }
            }
            
            close_short_command = {
                'command': 'execute_true_market_order',
                'order': {
                    'market_index': market_index,
                    'base_amount': base_amount,
                    'is_ask': False, # Buy to close short
                    'client_order_index': int(datetime.now().timestamp() * 1000 + 3) % 1000000,
                    'reduce_only': True,
                    'execution_price': close_short_execution_price
                }
            }
            
            # Close positions sequentially to avoid SDK race conditions
            # (parallel closing sometimes triggers SDK bugs)
            long_close_result = await self.run_worker_command(account1_config, close_long_command)
            await asyncio.sleep(0.5)  # Small delay to avoid SDK issues
            short_close_result = await self.run_worker_command(account2_config, close_short_command)
            
            results = [long_close_result, short_close_result]
            
            long_close, short_close = results
            
            # Log results with better error reporting
            if isinstance(long_close, dict) and long_close.get('success'):
                tx_hash = long_close.get('tx_hash', 'N/A')
                logger.info(f"✅ Closed long position (Account 1): TX {tx_hash[:16]}...")
            else:
                error_msg = 'Unknown error'
                if isinstance(long_close, dict):
                    error_msg = long_close.get('error') or long_close.get('message', 'Unknown')
                elif isinstance(long_close, Exception):
                    error_msg = str(long_close)
                logger.warning(f"⚠️  Long position close: {error_msg}")
            
            if isinstance(short_close, dict) and short_close.get('success'):
                tx_hash = short_close.get('tx_hash', 'N/A')
                logger.info(f"✅ Closed short position (Account 2): TX {tx_hash[:16]}...")
            else:
                error_msg = 'Unknown error'
                if isinstance(short_close, dict):
                    error_msg = short_close.get('error') or short_close.get('message', 'Unknown')
                    if 'traceback' in short_close:
                        logger.error(f"Traceback:\n{short_close['traceback']}")
                elif isinstance(short_close, Exception):
                    error_msg = str(short_close)
                logger.warning(f"⚠️  Short position close: {error_msg}")
                
        except Exception as e:
            logger.error(f"Error closing positions: {e}")
    
    async def run_continuous(self):
        """Run continuous trading with configured interval"""
        self.is_running = True
        
        # Update leverage on both accounts first
        await self.update_leverage_both_accounts()
        
        # Start background task for closing positions
        close_task = asyncio.create_task(self.close_positions_task())
        
        logger.info(f"Starting continuous trading with {self.config.interval_seconds}s interval")
        logger.info(f"Positions will close randomly between {self.config.min_close_delay}-{self.config.max_close_delay}s after opening")
        
        try:
            while self.is_running:
                self.trade_count += 1
                
                logger.info(f"\n{'='*60}")
                logger.info(f"Trade #{self.trade_count}")
                logger.info(f"{'='*60}")
                
                # Execute trade
                success, message = await self.execute_delta_neutral_trade()
                
                if success:
                    self.success_count += 1
                else:
                    logger.warning(f"✗ {message}")
                
                # Log statistics
                success_rate = (self.success_count / self.trade_count * 100) if self.trade_count > 0 else 0
                logger.info(f"Success rate: {self.success_count}/{self.trade_count} ({success_rate:.1f}%)")
                
                # Check if we've reached max trades
                if self.config.max_trades > 0 and self.trade_count >= self.config.max_trades:
                    logger.info(f"\nReached maximum trade limit ({self.config.max_trades})")
                    break
                
                # Wait before next trade with random delay
                open_delay = random.randint(self.config.min_open_delay, self.config.max_open_delay)
                logger.info(f"Waiting {open_delay}s until next trade (range: {self.config.min_open_delay}-{self.config.max_open_delay}s)...")
                await asyncio.sleep(open_delay)
                
        except KeyboardInterrupt:
            logger.info("\nReceived interrupt signal")
        finally:
            # Wait for any remaining open positions to be closed by the background task
            if self.open_positions:
                logger.info(f"\nWaiting for {len(self.open_positions)} remaining position(s) to close...")
                while self.open_positions:
                    await asyncio.sleep(1)
            
            # Now that all positions are closed, we can stop the background task
            self.is_running = False
            close_task.cancel()
            try:
                await close_task
            except asyncio.CancelledError:
                pass  # Expected on cancellation
            
            # Display market statistics
            if len(self.config.market_whitelist) > 1:
                logger.info("\n" + "="*60)
                logger.info("Market Statistics")
                logger.info("="*60)
                for market_id in sorted(self.market_stats.keys()):
                    stats = self.market_stats[market_id]
                    if stats['trades'] > 0:
                        success_rate = (stats['successful'] / stats['trades'] * 100) if stats['trades'] > 0 else 0
                        logger.info(f"  Market {market_id}: {stats['successful']}/{stats['trades']} trades ({success_rate:.1f}% success)")
            
            logger.info("Bot stopped")


async def main():
    """Main entry point"""
    logger.info("="*60)
    logger.info("Delta Neutral Volume Generation Bot for Lighter DEX")
    logger.info("="*60)
    
    # Load configuration
    try:
        config = BotConfig.from_env()
        config.validate()
    except Exception as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    
    # Display configuration
    logger.info("\nConfiguration:")
    logger.info(f"  Base URL: {config.base_url}")
    if 'testnet' in config.base_url.lower():
        logger.info("  ✓ Testnet mode - Safe for testing")
    else:
        logger.warning("  ⚠️  MAINNET MODE - Using real funds!")
    logger.info(f"  Market Whitelist: {config.market_whitelist} ({len(config.market_whitelist)} market(s))")
    logger.info(f"  Account 1 Index: {config.account1_index}")
    logger.info(f"  Account 2 Index: {config.account2_index}")
    if config.base_amount_in_usdt:
        logger.info(f"  Trade Size: ${config.base_amount_in_usdt:.2f} USDT (converted to asset at market price)")
    else:
        logger.info(f"  Base Amount: {config.base_amount / 10000:.4f}")
    logger.info(f"  Max Slippage: {config.max_slippage * 100:.2f}%")
    if config.use_dynamic_leverage:
        logger.info(f"  Leverage: DYNAMIC (market_max - {config.leverage_buffer} to market_max) 🎲")
    else:
        logger.info(f"  Leverage: {config.leverage}x (Fixed)")
    logger.info(f"  Margin Mode: {'Cross' if config.margin_mode == 0 else 'Isolated'}")
    logger.info(f"  Open New Trade Delay: {config.min_open_delay}-{config.max_open_delay}s (randomized) 🎲")
    logger.info(f"  Position Close Delay: {config.min_close_delay}-{config.max_close_delay}s (randomized)")
    logger.info(f"  Max Trades: {config.max_trades if config.max_trades > 0 else 'Unlimited'}")
    logger.info(f"  Batch Mode: {config.use_batch_mode}")
    logger.info("")
    
    # Validate leverage against Lighter API limits
    logger.info("Validating configuration against Lighter API...")
    try:
        await config.validate_with_api()
        max_leverage = await config.get_market_max_leverage()
        logger.info(f"✅ Leverage validation passed")
        logger.info(f"   Market {config.market_index} max leverage: {max_leverage}x")
        logger.info(f"   Your configured leverage: {config.leverage}x")
    except Exception as e:
        logger.error(f"❌ Validation failed: {e}")
        logger.error("\nPlease check your configuration and try again.")
        sys.exit(1)
    
    logger.info("")
    
    # Create and run orchestrator
    orchestrator = DeltaNeutralOrchestrator(config)
    await orchestrator.run_continuous()
    
    logger.info("\nExiting...")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot connections closed")
        print("\nExiting...")
        sys.exit(0)
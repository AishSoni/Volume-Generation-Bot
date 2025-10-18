"""
Delta Neutral Volume Generation Bot for Lighter DEX - Orchestrator

This orchestrator manages isolated worker processes for each account to avoid
signer conflicts. It coordinates simultaneous trades and position closing.
"""

import asyncio
import json
import logging
import random
import subprocess
import sys
from datetime import datetime
from typing import Optional, Tuple, Dict
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
    """Orchestrates trading across two isolated account workers"""
    
    def __init__(self, config: BotConfig):
        self.config = config
        self.trade_count = 0
        self.success_count = 0
        self.is_running = False
        self.open_positions = []  # Track open positions for closing
        
    async def get_current_price(self) -> Optional[Tuple[float, float]]:
        """Get current best bid and ask from order book"""
        try:
            configuration = lighter.Configuration(self.config.base_url)
            api_client = lighter.ApiClient(configuration)
            order_api = lighter.OrderApi(api_client)
            
            order_book = await order_api.order_book_orders(
                market_id=self.config.market_index,
                limit=1
            )
            
            await api_client.close()
            
            if order_book.asks and order_book.bids:
                best_ask = float(order_book.asks[0].price)
                best_bid = float(order_book.bids[0].price)
                return best_bid, best_ask
            else:
                logger.warning("Order book has no bids or asks")
                return None, None
                
        except Exception as e:
            logger.error(f"Error fetching current price: {e}")
            return None, None
    
    async def run_worker_command(self, account_config: dict, command_config: dict) -> dict:
        """Run a worker process with given configuration"""
        try:
            # Prepare full configuration
            full_config = {
                'account': account_config,
                **command_config
            }
            
            # Start worker process
            process = await asyncio.create_subprocess_exec(
                sys.executable,  # Use same Python interpreter
                'account_worker.py',
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Send configuration to worker
            config_json = json.dumps(full_config)
            stdout, stderr = await process.communicate(input=config_json.encode())
            
            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else 'Unknown error'
                return {'success': False, 'error': f'Worker failed: {error_msg}'}
            
            # Parse result
            result = json.loads(stdout.decode())
            return result
            
        except Exception as e:
            return {'success': False, 'error': f'Worker exception: {str(e)}'}
    
    async def update_leverage_both_accounts(self):
        """Update leverage on both accounts"""
        logger.info(f"Updating leverage to {self.config.leverage}x (margin mode: {'cross' if self.config.margin_mode == 0 else 'isolated'})")
        
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
                'market_index': self.config.market_index,
                'leverage': self.config.leverage,
                'margin_mode': self.config.margin_mode
            }
        }
        
        # Update leverage for both accounts in parallel
        results = await asyncio.gather(
            self.run_worker_command(account1_config, leverage_command),
            self.run_worker_command(account2_config, leverage_command),
            return_exceptions=True
        )
        
        logger.info("✅ Leverage updated on both accounts")
        return True
    
    async def execute_delta_neutral_trade(self) -> Tuple[bool, str]:
        """Execute simultaneous long and short market orders using isolated workers"""
        try:
            # Get current bid and ask
            best_bid, best_ask = await self.get_current_price()
            if not best_bid or not best_ask:
                return False, "Failed to get current price"

            # --- PRE-TRADE SAFEGUARD: Check Bid-Ask Spread ---
            spread = best_ask - best_bid
            spread_percentage = (spread / best_ask) * 100
            max_spread_percentage = 0.1  # Allow up to 0.1% spread

            if spread_percentage > max_spread_percentage:
                logger.warning(f"Spread ({spread_percentage:.4f}%) exceeds max ({max_spread_percentage}%) - skipping trade")
                return False, "Spread too wide"
            
            # Calculate base_amount (convert from USDT if specified)
            if self.config.base_amount_in_usdt:
                # Use mid-price for conversion
                mid_price = (best_bid + best_ask) / 2
                # Convert USDT to base asset amount (with 4 decimal precision)
                base_amount = int((self.config.base_amount_in_usdt / mid_price) * 10000)
                logger.info(f"Using BASE_AMOUNT_IN_USDT: ${self.config.base_amount_in_usdt:.2f} @ ${mid_price:.2f} = {base_amount / 10000:.4f} ETH")
            else:
                base_amount = self.config.base_amount
            
            logger.info(f"Executing delta neutral trade:")
            logger.info(f"  Base amount: {base_amount / 10000:.4f}")
            logger.info(f"  Best Bid: ${best_bid:.2f}, Best Ask: ${best_ask:.2f}")
            logger.info(f"  Spread: ${spread:.2f} ({spread_percentage:.3f}%)")
            
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
            
            # Prepare order commands
            timestamp_ms = int(datetime.now().timestamp() * 1000)
            
            # For a true market order, we set a very wide price boundary.
            # For a buy order, we set a very high price.
            # For a sell order, we set a very low price (e.g., 1).
            long_execution_price = 999999999
            short_execution_price = 1

            long_command = {
                'command': 'execute_true_market_order',
                'order': {
                    'market_index': self.config.market_index,
                    'base_amount': base_amount,
                    'is_ask': False,  # Buy = Long
                    'client_order_index': timestamp_ms % 1000000,
                    'execution_price': long_execution_price
                }
            }
            
            short_command = {
                'command': 'execute_true_market_order',
                'order': {
                    'market_index': self.config.market_index,
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
                # Schedule position closing
                close_delay = random.randint(self.config.min_close_delay, self.config.max_close_delay)
                position_info = {
                    'market_index': self.config.market_index,
                    'base_amount': base_amount,
                    'close_time': asyncio.get_event_loop().time() + close_delay,
                    'close_delay': close_delay,
                    'trade_number': self.trade_count
                }
                self.open_positions.append(position_info)
                
                logger.info(f"✅ Delta neutral trade executed successfully")
                logger.info(f"📅 Position will close in {close_delay} seconds")
                return True, "Success"
            else:
                return False, "One or both orders failed"
                
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
                        logger.info(f"\n{'='*60}")
                        logger.info(f"Closing positions from Trade #{pos['trade_number']}")
                        logger.info(f"{'='*60}")
                        await self.close_position_pair(
                            pos['market_index'],
                            pos['base_amount']
                        )
                    
                    # Only update the list after closing is complete
                    self.open_positions = remaining_positions
                
                await asyncio.sleep(1)  # Check every second
                
            except Exception as e:
                logger.error(f"Error in close positions task: {e}")
                await asyncio.sleep(5)
    
    async def close_position_pair(self, market_index: int, base_amount: int):
        """Close both long and short positions"""
        try:
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
                
                # Wait before next trade
                logger.info(f"Waiting {self.config.interval_seconds}s until next trade...")
                await asyncio.sleep(self.config.interval_seconds)
                
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
    logger.info(f"  Market Index: {config.market_index}")
    logger.info(f"  Account 1 Index: {config.account1_index}")
    logger.info(f"  Account 2 Index: {config.account2_index}")
    if config.base_amount_in_usdt:
        logger.info(f"  Trade Size: ${config.base_amount_in_usdt:.2f} USDT (converted to asset at market price)")
    else:
        logger.info(f"  Base Amount: {config.base_amount / 10000:.4f}")
    logger.info(f"  Max Slippage: {config.max_slippage * 100:.2f}%")
    logger.info(f"  Leverage: {config.leverage}x")
    logger.info(f"  Margin Mode: {'Cross' if config.margin_mode == 0 else 'Isolated'}")
    logger.info(f"  Interval: {config.interval_seconds}s")
    logger.info(f"  Position Close Delay: {config.min_close_delay}-{config.max_close_delay}s")
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
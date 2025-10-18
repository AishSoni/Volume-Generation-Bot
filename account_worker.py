#!/usr/bin/env python3
"""
Single Account Worker - Executes trades for one account only
This runs as an isolated process to avoid signer conflicts
"""

import asyncio
import sys
import os
import json
import random
from datetime import datetime
from dotenv import load_dotenv
import lighter

load_dotenv()

class SingleAccountWorker:
    """Worker that manages a single account for trading"""
    
    def __init__(self, account_config: dict):
        self.config = account_config
        self.client = None
        self.leverage_updated = False
        
    async def initialize(self):
        """Initialize the account client"""
        try:
            self.client = lighter.SignerClient(
                url=self.config['base_url'],
                private_key=self.config['private_key'],
                account_index=self.config['account_index'],
                api_key_index=self.config['api_key_index'],
            )
            return True
        except Exception as e:
            print(f"Error initializing worker: {e}", file=sys.stderr)
            return False
    
    async def update_leverage(self, market_index: int, leverage: int, margin_mode: int):
        """Update leverage for the account on specified market"""
        try:
            if self.leverage_updated:
                return True  # Already updated
                
            result = await self.client.update_leverage(
                market_index=market_index,
                margin_mode=margin_mode,
                leverage=leverage
            )
            
            self.leverage_updated = True
            return True
        except Exception as e:
            print(f"Warning: Could not update leverage: {e}", file=sys.stderr)
            # Don't fail if leverage update fails - continue with default
            return True
    
    async def execute_order(self, order_params: dict) -> dict:
        """
        Execute a single order
        Returns: dict with success status and details
        """
        try:
            market_index = order_params['market_index']
            base_amount = order_params['base_amount']
            price_limit = order_params['price_limit']
            is_ask = order_params['is_ask']
            client_order_index = order_params.get('client_order_index', 0)
            
            # Execute market order with slippage protection
            result = await self.client.create_market_order(
                market_index=market_index,
                client_order_index=client_order_index,
                base_amount=base_amount,
                avg_execution_price=price_limit,
                is_ask=is_ask,
            )
            
            # Parse result tuple: (CreateOrder, RespSendTx, error)
            create_order, resp, error = result
            
            if error:
                return {
                    'success': False,
                    'error': error,
                    'timestamp': datetime.now().isoformat()
                }
            
            if resp and resp.code == 200:
                return {
                    'success': True,
                    'tx_hash': resp.tx_hash,
                    'timestamp': datetime.now().isoformat(),
                    'predicted_time': resp.predicted_execution_time_ms
                }
            else:
                return {
                    'success': False,
                    'error': f"API returned code {resp.code if resp else 'None'}: {resp.message if resp else 'No response'}",
                    'timestamp': datetime.now().isoformat()
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def close_position(self, market_index: int, position_side: str, base_amount: int, price_limit: int) -> dict:
        """
        Close an open position by placing an opposite reduce-only order
        position_side: 'long' or 'short'
        base_amount: the size to close (same as opening size)
        price_limit: price limit for the close order
        """
        try:
            # Determine order direction
            # For a long position, we sell (is_ask=True)
            # For a short position, we buy (is_ask=False)
            is_ask = position_side.lower() == 'long'
            
            # Place reduce-only market order to close position
            close_result = await self.client.create_market_order(
                market_index=market_index,
                client_order_index=int(datetime.now().timestamp() * 1000) % 1000000,
                base_amount=base_amount,
                avg_execution_price=price_limit,
                is_ask=is_ask,
                reduce_only=True  # Critical: this ensures we only close, not open new positions
            )
            
            # Parse result: (order, response, error)
            create_order, resp, error = close_result
            
            if error:
                return {
                    'success': False,
                    'error': f'Close order failed: {error}',
                    'timestamp': datetime.now().isoformat()
                }
            
            # Extract tx_hash safely like the reference code does
            tx_hash = None
            if resp:
                tx_hash = getattr(resp, 'tx_hash', None) or getattr(resp, 'txHash', None)
            
            if tx_hash:
                return {
                    'success': True,
                    'tx_hash': tx_hash,
                    'timestamp': datetime.now().isoformat(),
                    'closed_size': base_amount,
                    'message': f'Closed {position_side} position'
                }
            else:
                # No tx_hash but no error either - might have succeeded
                return {
                    'success': True,
                    'tx_hash': 'N/A',
                    'timestamp': datetime.now().isoformat(),
                    'closed_size': base_amount,
                    'message': f'Closed {position_side} position (no tx_hash in response)'
                }
                
        except Exception as e:
            import traceback
            return {
                'success': False,
                'error': f'Exception during close: {str(e)}',
                'traceback': traceback.format_exc(),
                'timestamp': datetime.now().isoformat()
            }
    
    async def close(self):
        """Close the client connection"""
        if self.client:
            await self.client.close()


async def main():
    """Main worker process"""
    # Read configuration from stdin (JSON)
    config_json = sys.stdin.read()
    config = json.loads(config_json)
    
    worker = SingleAccountWorker(config['account'])
    
    # Initialize
    if not await worker.initialize():
        result = {'success': False, 'error': 'Failed to initialize'}
        print(json.dumps(result))
        sys.exit(1)
    
    command = config.get('command', 'execute_order')
    
    if command == 'update_leverage':
        # Update leverage first
        await worker.update_leverage(
            market_index=config['leverage']['market_index'],
            leverage=config['leverage']['leverage'],
            margin_mode=config['leverage']['margin_mode']
        )
        result = {'success': True, 'message': 'Leverage updated'}
        
    elif command == 'execute_order':
        # Execute order
        result = await worker.execute_order(config['order'])
        
    elif command == 'close_position':
        # Close position
        result = await worker.close_position(
            market_index=config['close']['market_index'],
            position_side=config['close']['position_side'],
            base_amount=config['close']['base_amount'],
            price_limit=config['close']['price_limit']
        )
        
    else:
        result = {'success': False, 'error': f'Unknown command: {command}'}
    
    # Output result as JSON
    print(json.dumps(result))
    
    # Clean up
    await worker.close()


if __name__ == "__main__":
    asyncio.run(main())

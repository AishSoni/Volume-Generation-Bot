#!/usr/bin/env python3
"""
Isolated Account Worker

Runs as a separate process to execute trades for a single account.
This isolation prevents signer conflicts when managing multiple accounts.
"""

import asyncio
import sys
import json
from dotenv import load_dotenv
import lighter

load_dotenv()


class SingleAccountWorker:
    """Manages a single trading account in an isolated process"""
    
    def __init__(self, account_config: dict):
        self.config = account_config
        self.client = None
        self.leverage_updated = False
        
    async def initialize(self) -> bool:
        """
        Initialize the Lighter SignerClient for this account.
        
        Returns:
            True if successful, False otherwise
        """
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
    
    async def update_leverage(self, market_index: int, leverage: int, margin_mode: int) -> bool:
        """
        Update leverage settings for the account.
        
        Args:
            market_index: Market ID
            leverage: Leverage multiplier
            margin_mode: 0 for cross, 1 for isolated
            
        Returns:
            True if successful
        """
        try:
            if self.leverage_updated:
                return True
                
            await self.client.update_leverage(
                market_index=market_index,
                margin_mode=margin_mode,
                leverage=leverage
            )
            
            self.leverage_updated = True
            return True
        except Exception as e:
            print(f"Warning: Could not update leverage: {e}", file=sys.stderr)
            return True  # Continue with default leverage
    
    async def execute_limit_order(self, order_params: dict) -> dict:
        """
        Execute a POST-ONLY limit order at specified price.
        
        Args:
            order_params: Order parameters including market_index, base_amount,
                         limit_price, is_ask, and optional reduce_only
                         
        Returns:
            Dictionary with success status, order_id, tx_hash or error message
        """
        try:
            result = await self.client.create_limit_order(
                market_index=order_params['market_index'],
                client_order_index=order_params['client_order_index'],
                base_amount=order_params['base_amount'],
                price_limit=order_params['limit_price'],
                is_ask=order_params['is_ask'],
                post_only=True,  # Critical: ensures we're a maker, not taker
                reduce_only=order_params.get('reduce_only', False)
            )

            create_order, resp, error = result

            if error:
                return {'success': False, 'error': error}

            if resp and resp.code == 200:
                return {
                    'success': True, 
                    'tx_hash': resp.tx_hash,
                    'order_id': create_order.order_id if create_order else None
                }
            
            error_msg = f"API Error {resp.code if resp else 'N/A'}"
            if resp and resp.message:
                error_msg += f": {resp.message}"
            return {'success': False, 'error': error_msg}

        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def cancel_order(self, order_params: dict) -> dict:
        """
        Cancel a limit order by order_id.
        
        Args:
            order_params: Dict with market_index and order_id
            
        Returns:
            Dictionary with success status
        """
        try:
            result = await self.client.cancel_limit_order(
                market_index=order_params['market_index'],
                order_id=order_params['order_id']
            )
            
            _, resp, error = result
            
            if error:
                return {'success': False, 'error': error}
            
            if resp and resp.code == 200:
                return {'success': True, 'message': 'Order cancelled'}
            
            return {'success': False, 'error': f"API Error {resp.code if resp else 'N/A'}"}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def get_order_status(self, order_params: dict) -> dict:
        """
        Check if an order has been filled.
        
        Args:
            order_params: Dict with market_index and order_id
            
        Returns:
            Dictionary with filled status and filled amount
        """
        try:
            # Query active orders for this account
            configuration = lighter.Configuration(self.config['base_url'])
            api_client = lighter.ApiClient(configuration)
            order_api = lighter.OrderApi(api_client)
            
            # Get active orders for this market
            orders = await order_api.orders(
                by='account_index',
                value=str(self.config['account_index']),
                market_id=order_params['market_index'],
                is_active=True
            )
            
            await api_client.close()
            
            # Check if our order is still active
            order_id = order_params['order_id']
            if orders.orders:
                for order in orders.orders:
                    if order.order_id == order_id:
                        # Order still active, not filled
                        return {
                            'success': True,
                            'filled': False,
                            'remaining_amount': order.amount_base
                        }
            
            # Order not found in active orders = fully filled or cancelled
            return {'success': True, 'filled': True}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def execute_true_market_order(self, order_params: dict) -> dict:
        """
        Execute a market order with worst-case price limit.
        
        Args:
            order_params: Order parameters including market_index, base_amount,
                         execution_price, is_ask, and optional reduce_only
                         
        Returns:
            Dictionary with success status, tx_hash or error message
        """
        try:
            result = await self.client.create_market_order(
                market_index=order_params['market_index'],
                client_order_index=order_params['client_order_index'],
                base_amount=order_params['base_amount'],
                avg_execution_price=order_params['execution_price'],
                is_ask=order_params['is_ask'],
                reduce_only=order_params.get('reduce_only', False)
            )

            create_order, resp, error = result

            if error:
                return {'success': False, 'error': error}

            if resp and resp.code == 200:
                return {'success': True, 'tx_hash': resp.tx_hash}
            
            error_msg = f"API Error {resp.code if resp else 'N/A'}"
            if resp and resp.message:
                error_msg += f": {resp.message}"
            return {'success': False, 'error': error_msg}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def close(self):
        """Close the client connection and cleanup resources"""
        if self.client:
            await self.client.close()


async def main():
    """
    Main worker process entry point.
    Reads configuration from stdin, executes command, outputs result to stdout.
    """
    config_json = sys.stdin.read()
    config = json.loads(config_json)
    
    worker = SingleAccountWorker(config['account'])
    
    if not await worker.initialize():
        result = {'success': False, 'error': 'Failed to initialize worker'}
        print(json.dumps(result))
        sys.exit(1)
    
    command = config.get('command')
    
    if command == 'update_leverage':
        await worker.update_leverage(
            market_index=config['leverage']['market_index'],
            leverage=config['leverage']['leverage'],
            margin_mode=config['leverage']['margin_mode']
        )
        result = {'success': True, 'message': 'Leverage updated'}
    elif command == 'execute_true_market_order':
        result = await worker.execute_true_market_order(config['order'])
    elif command == 'execute_limit_order':
        result = await worker.execute_limit_order(config['order'])
    elif command == 'cancel_order':
        result = await worker.cancel_order(config['order'])
    elif command == 'get_order_status':
        result = await worker.get_order_status(config['order'])
    else:
        result = {'success': False, 'error': f'Unknown command: {command}'}
    
    print(json.dumps(result))
    await worker.close()


if __name__ == "__main__":
    asyncio.run(main())
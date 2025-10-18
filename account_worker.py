#!/usr/bin/env python3
"""
Single Account Worker - Executes trades for one account only
This runs as an isolated process to avoid signer conflicts
"""

import asyncio
import sys
import os
import json
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
    


    async def execute_true_market_order(self, order_params: dict) -> dict:
        """
        Execute a true market order by providing a worst-case price limit.
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
            else:
                return {'success': False, 'error': f"API Error {resp.code if resp else 'N/A'}: {resp.message if resp else 'No response'}"}

        except Exception as e:
            return {'success': False, 'error': str(e)}



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
    
    command = config.get('command')
    
    if command == 'update_leverage':
        # Update leverage
        await worker.update_leverage(
            market_index=config['leverage']['market_index'],
            leverage=config['leverage']['leverage'],
            margin_mode=config['leverage']['margin_mode']
        )
        result = {'success': True, 'message': 'Leverage updated'}

    elif command == 'execute_true_market_order':
        # Execute a true market order
        result = await worker.execute_true_market_order(config['order'])
        
    else:
        result = {'success': False, 'error': f'Unknown command: {command}'}
    
    # Output result as JSON
    print(json.dumps(result))
    
    # Clean up
    await worker.close()


if __name__ == "__main__":
    asyncio.run(main())
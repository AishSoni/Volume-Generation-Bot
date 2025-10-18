import asyncio
import sys
import os
from dotenv import load_dotenv
import lighter

load_dotenv()

async def check_both_accounts():
    print("="*70)
    print("LIGHTER DEX BALANCE CHECK")
    print("="*70)
    
    base_url = os.getenv("BASE_URL")
    account1_index = int(os.getenv("ACCOUNT1_INDEX"))
    account2_index = int(os.getenv("ACCOUNT2_INDEX"))
    
    print(f"\nNetwork: {base_url}")
    
    try:
        configuration = lighter.Configuration(base_url)
        api_client = lighter.ApiClient(configuration)
        account_api = lighter.AccountApi(api_client)
        
        # Account 1
        print(f"\nACCOUNT 1 - Index {account1_index}")
        accounts1 = await account_api.account(by="index", value=str(account1_index))
        if accounts1.accounts:
            acc1 = accounts1.accounts[0]
            print(f"  Available: ${float(acc1.available_balance):.2f}")
            print(f"  Positions: {len(acc1.positions)}")
        
        # Account 2
        print(f"\nACCOUNT 2 - Index {account2_index}")
        accounts2 = await account_api.account(by="index", value=str(account2_index))
        if accounts2.accounts:
            acc2 = accounts2.accounts[0]
            print(f"  Available: ${float(acc2.available_balance):.2f}")
            print(f"  Positions: {len(acc2.positions)}")
        
        await api_client.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_both_accounts())

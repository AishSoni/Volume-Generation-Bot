# Delta Neutral Volume Generation Bot for Lighter DEX# Delta Neutral Volume Generation Bot for Lighter DEX



A sophisticated trading bot that executes delta-neutral strategies on Lighter DEX by simultaneously opening long and short positions across two accounts. The bot automatically closes positions after a configurable delay, generating genuine trading volume while maintaining market neutrality.A sophisticated trading bot that executes delta-neutral strategies on Lighter DEX by simultaneously opening long and short positions across two accounts with equal notional value. This generates genuine trading volume while maintaining market neutrality.



## 🎯 Key Features## 📚 Documentation



- **Delta Neutral Strategy**: Simultaneously executes long (buy) and short (sell) orders with identical notional amounts**📖 Complete documentation is available in the [`docs/`](docs/) folder.**

- **Automatic Position Closing**: Closes positions after a random delay (30-50 seconds by default)

- **Configurable Leverage**: Set leverage and margin mode via environment variables (default: 10x cross margin)**New users should start with: [`docs/START_HERE.md`](docs/START_HERE.md)**

- **Dual Account Management**: Uses isolated worker processes to manage two separate accounts

- **Market Order Execution**: Uses market orders with configurable slippage protectionKey documentation:

- **Reduce-Only Closing**: Safely closes positions without risk of opening new ones- **[START_HERE.md](docs/START_HERE.md)** - Complete overview and quick reference

- **Continuous Operation**: Runs continuously with configurable intervals- **[FIRST_TIME_SETUP.md](docs/FIRST_TIME_SETUP.md)** - Step-by-step setup guide

- **Comprehensive Logging**: Detailed logs for monitoring and debugging- **[TESTNET_FUNDS_GUIDE.md](docs/TESTNET_FUNDS_GUIDE.md)** - ⚠️ CRITICAL: Testnet $500 budget management

- **Native Windows Support**: Runs directly on Windows using Python virtual environment- **[PRE_LAUNCH_CHECKLIST.md](docs/PRE_LAUNCH_CHECKLIST.md)** - Pre-flight checklist

- **[QUICKSTART.md](docs/QUICKSTART.md)** - Quick command reference

## 📋 Prerequisites- **[docs/README.md](docs/README.md)** - Full documentation index



- Python 3.12+ installed on Windows---

- Two Lighter DEX accounts with:

  - Private keys## 🎯 Features

  - Account indices

  - API key indices- **Delta Neutral Strategy**: Simultaneously executes long (buy) and short (sell) orders with identical notional amounts

- Sufficient balance in both accounts for trading (testnet provides $500 per account)- **Dual Account Management**: Manages two separate accounts for long and short positions

- **Market Order Execution**: Uses market orders with configurable slippage protection

## 🚀 Quick Start- **Batch Transaction Support**: Optional batch mode for improved atomicity

- **Continuous Operation**: Runs continuously with configurable intervals

### 1. Set Up Python Environment- **Docker Support**: Fully containerized for easy deployment on any platform

- **Comprehensive Logging**: Detailed logs for monitoring and debugging

```powershell- **Configurable Parameters**: All trading parameters configurable via environment variables

# Create virtual environment

python -m venv venv## 📋 Prerequisites



# Activate virtual environment- Docker and Docker Compose installed on your system

.\venv\Scripts\Activate.ps1- Two Lighter DEX accounts with API keys

- Sufficient balance in both accounts for trading

# Install dependencies

pip install -r requirements.txt## 🚀 Quick Start



# Install Lighter SDK### 1. Clone or Download the Project

pip install -e .\lighter-python

``````bash

cd "e:\Volume Generation Bot"

### 2. Configure Environment Variables```



Copy `.env.example` to `.env` and configure your settings:### 2. Configure Environment Variables



```powershellCopy the example environment file and edit it with your credentials:

Copy-Item .env.example .env

notepad .env```bash

```cp .env.example .env

```

**Critical Configuration Parameters:**

Edit `.env` file with your account details:

```env

# Network Configuration```env

BASE_URL=https://testnet.zklighter.elliot.ai  # Testnet (safe for testing)# Account 1 (Long positions)

# BASE_URL=https://api.lighter.xyz             # Mainnet (uses real funds!)ACCOUNT1_PRIVATE_KEY=0xYOUR_ACCOUNT1_PRIVATE_KEY_HERE

ACCOUNT1_INDEX=1

# Account 1 (Long Positions)ACCOUNT1_API_KEY_INDEX=0

ACCOUNT1_PRIVATE_KEY=0xyour_private_key_here

ACCOUNT1_INDEX=16# Account 2 (Short positions)

ACCOUNT1_API_KEY_INDEX=3ACCOUNT2_PRIVATE_KEY=0xYOUR_ACCOUNT2_PRIVATE_KEY_HERE

ACCOUNT2_INDEX=2

# Account 2 (Short Positions)ACCOUNT2_API_KEY_INDEX=0

ACCOUNT2_PRIVATE_KEY=0xyour_private_key_here

ACCOUNT2_INDEX=15# Trading Parameters

ACCOUNT2_API_KEY_INDEX=3MARKET_INDEX=0

BASE_AMOUNT=100000

# Trading ParametersMAX_SLIPPAGE=0.02

BASE_AMOUNT=100              # 0.01 ETH (100 / 10000)INTERVAL_SECONDS=60

MAX_SLIPPAGE=0.1            # 10% slippage protectionMAX_TRADES=0

MARKET_INDEX=0              # ETH-PERP market```



# Leverage Configuration### 3. Build and Run with Docker

LEVERAGE=10                 # 10x leverage

MARGIN_MODE=0              # 0=cross, 1=isolated```bash

# Build the Docker image

# Position Closingdocker-compose build

MIN_CLOSE_DELAY=30         # Minimum seconds before closing

MAX_CLOSE_DELAY=50         # Maximum seconds before closing# Start the bot

docker-compose up -d

# Bot Operation

INTERVAL_SECONDS=60        # Wait time between NEW trades# View logs

MAX_TRADES=3              # Stop after N trades (0=unlimited)docker-compose logs -f

```

# Stop the bot

### 3. Run the Botdocker-compose down

```

```powershell

# Activate virtual environment if not already active## ⚙️ Configuration

.\venv\Scripts\Activate.ps1

### Environment Variables

# Run the orchestrator

python delta_neutral_orchestrator.py| Variable | Description | Default | Required |

```|----------|-------------|---------|----------|

| `BASE_URL` | Lighter API base URL | `https://testnet.zklighter.elliot.ai` | No |

## 📁 Project Structure| `ACCOUNT1_PRIVATE_KEY` | Private key for Account 1 (Long) | - | Yes |

| `ACCOUNT1_INDEX` | Account index for Account 1 | - | Yes |

```| `ACCOUNT1_API_KEY_INDEX` | API key index for Account 1 | `0` | No |

Volume Generation Bot/| `ACCOUNT2_PRIVATE_KEY` | Private key for Account 2 (Short) | - | Yes |

├── .env                              # Your configuration (do not commit!)| `ACCOUNT2_INDEX` | Account index for Account 2 | - | Yes |

├── .env.example                      # Configuration template| `ACCOUNT2_API_KEY_INDEX` | API key index for Account 2 | `0` | No |

├── .gitignore                        # Git ignore rules| `MARKET_INDEX` | Market to trade (0 = ETH-USD) | `0` | No |

├── README.md                         # This file| `BASE_AMOUNT` | Base asset amount per trade | `100000` | No |

├── requirements.txt                  # Python dependencies| `MAX_SLIPPAGE` | Maximum acceptable slippage | `0.02` (2%) | No |

├── config.py                         # Configuration management| `INTERVAL_SECONDS` | Time between trades | `60` | No |

├── account_worker.py                 # Isolated account worker process| `MAX_TRADES` | Maximum trades (0 = unlimited) | `0` | No |

├── delta_neutral_orchestrator.py    # Main orchestrator (RUN THIS)| `USE_BATCH_MODE` | Use batch transactions | `false` | No |

├── lighter-python/                   # Lighter SDK

├── references/                       # Reference implementation code### Trading Parameters Explained

└── venv/                            # Python virtual environment

```- **BASE_AMOUNT**: Amount in base asset with precision. For ETH (4 decimals):

  - **IMPORTANT**: Testnet provides only $500 per account!

## 🔧 Architecture  - `1000` = 0.0001 ETH (~$0.20 at $2000/ETH) - Recommended for testing

  - `5000` = 0.0005 ETH (~$1.00 at $2000/ETH) - Good balance (default)

The bot uses a **multi-process architecture** to avoid conflicts with the Lighter SDK's C library signer:  - `10000` = 0.001 ETH (~$2.00 at $2000/ETH) - Moderate

  - `100000` = 0.01 ETH (~$20 at $2000/ETH) - ⚠️ Too large for testnet!

1. **Orchestrator** (`delta_neutral_orchestrator.py`):  - See TESTNET_FUNDS_GUIDE.md for detailed fund management

   - Manages overall trading flow

   - Coordinates two isolated worker processes- **MAX_SLIPPAGE**: Maximum price deviation acceptable:

   - Schedules position opening and closing  - `0.01` = 1% slippage

   - Handles timing and delays  - `0.02` = 2% slippage (recommended)

  - `0.05` = 5% slippage

2. **Workers** (`account_worker.py`):

   - Each runs as a separate Python process- **INTERVAL_SECONDS**: Time to wait between trade executions:

   - Manages a single SignerClient instance  - `60` = 1 minute (recommended for testing)

   - Executes orders for one account  - `300` = 5 minutes

   - Communicates via JSON stdin/stdout  - `3600` = 1 hour



This architecture ensures that each account has its own isolated C library signer, preventing nonce conflicts.## 📊 How It Works



## ⚙️ Configuration Details1. **Initialization**: Bot connects to both accounts and verifies connectivity

2. **Price Discovery**: Fetches current market price from order book

### Leverage Settings3. **Simultaneous Execution**: 

   - Account 1: Places market BUY order (long position)

```env   - Account 2: Places market SELL order (short position)

LEVERAGE=10          # 1-20x leverage4. **Delta Neutral**: Both orders have identical notional value, maintaining market neutrality

MARGIN_MODE=0        # 0=cross margin, 1=isolated margin5. **Repeat**: Waits for configured interval and repeats

```

### Example Trade Flow

Cross margin (0) shares margin across all positions. Isolated margin (1) limits risk to each position separately.

```

### Position ClosingCurrent Price: $2,000

Base Amount: 0.1 ETH

```envMax Slippage: 2%

MIN_CLOSE_DELAY=30   # Minimum seconds to hold position

MAX_CLOSE_DELAY=50   # Maximum seconds to hold positionAccount 1 (Long):  Buy  0.1 ETH at max price $2,040 (2% above)

```Account 2 (Short): Sell 0.1 ETH at min price $1,960 (2% below)



The bot picks a random delay in this range for each trade, creating natural variation in position hold times.Net Position: 0 ETH (delta neutral)

Volume Generated: ~$400 total

### Trading Amount```



```env## 🐳 Docker Commands

BASE_AMOUNT=100      # Represents 0.01 ETH (100 / 10000)

```### Build and Run

```bash

The base amount is scaled by 10,000. So:# Build the image

- 100 = 0.01 ETHdocker-compose build

- 1000 = 0.1 ETH

- 10000 = 1 ETH# Start in detached mode

docker-compose up -d

### Slippage Protection

# Start with logs

```envdocker-compose up

MAX_SLIPPAGE=0.1     # 10% maximum slippage

```# Rebuild and start

docker-compose up -d --build

This prevents orders from executing at prices too far from the mid-price. Market orders use the mid-price ± slippage as price limits.```



## 📊 How It Works### Monitoring

```bash

1. **Leverage Update**: On startup, sets leverage to configured value on both accounts# View logs

2. **Trade Execution**:docker-compose logs -f

   - Fetches current market price from order book

   - Calculates price limits with slippage protection# View last 100 lines

   - Simultaneously places long order (Account 1) and short order (Account 2)docker-compose logs --tail=100

   - Records position details and scheduled close time

3. **Position Closing**:# Check container status

   - Background task monitors scheduled close timesdocker-compose ps

   - When time arrives, places reduce-only orders to close positions```

   - Uses fresh market prices for closing

4. **Repeat**: Waits for configured interval, then executes next trade### Management

```bash

## 🔍 Monitoring# Stop the bot

docker-compose down

The bot provides detailed logging:

# Stop and remove volumes

```docker-compose down -v

2025-10-17 22:32:52 - INFO - ============================================================

2025-10-17 22:32:52 - INFO - Trade #1# Restart the bot

2025-10-17 22:32:52 - INFO - ============================================================docker-compose restart

2025-10-17 22:32:52 - INFO - Executing delta neutral trade:

2025-10-17 22:32:52 - INFO -   Base amount: 0.0100# Execute command in container

2025-10-17 22:32:52 - INFO -   Current price: $3780.00docker-compose exec delta-neutral-bot python --version

2025-10-17 22:32:52 - INFO -   Long max price: $4158.00```

2025-10-17 22:32:52 - INFO -   Short min price: $3402.00

2025-10-17 22:32:58 - INFO - ✅ Long order (Account 1): TX 28bf0d3346d88285...### Debugging

2025-10-17 22:32:58 - INFO - ✅ Short order (Account 2): TX b2db284a4d50dedd...```bash

2025-10-17 22:32:58 - INFO - ✅ Delta neutral trade executed successfully# Access container shell

2025-10-17 22:32:58 - INFO - 📅 Position will close in 48 secondsdocker-compose exec delta-neutral-bot /bin/bash

2025-10-17 22:32:58 - INFO - Success rate: 1/1 (100.0%)

```# View log file inside container

docker-compose exec delta-neutral-bot cat delta_neutral_bot.log

## ⚠️ Important Notes

# Copy logs to host

### Testnet vs Mainnetdocker cp lighter-delta-neutral-bot:/app/delta_neutral_bot.log ./logs/

```

**Always test on testnet first!**

## 📁 Project Structure

- **Testnet**: `https://testnet.zklighter.elliot.ai` - Uses test funds ($500 limit per account)

- **Mainnet**: `https://api.lighter.xyz` - Uses REAL money!```

Volume Generation Bot/

The bot logs a warning if running on mainnet.├── delta_neutral_bot.py    # Main bot logic

├── config.py                # Configuration management

### Account Indices├── requirements.txt         # Python dependencies

├── Dockerfile              # Docker image definition

Each account has:├── docker-compose.yml      # Docker Compose configuration

- **Private Key**: For signing transactions├── .env.example            # Example environment variables

- **Account Index**: Your account number on Lighter (find in account settings)├── .env                    # Your environment variables (gitignored)

- **API Key Index**: Which API key to use (usually 3)├── logs/                   # Log files directory

└── lighter-python/         # Lighter Python SDK

These must match correctly or transactions will fail.    ├── docs/               # API documentation

    ├── examples/           # Example scripts

### Position Management    └── .others/            # SDK source code

```

The bot:

- Opens positions with configurable leverage## 🔒 Security Best Practices

- Holds positions for random delays (30-50s default)

- Closes positions with `reduce_only=True` to prevent accidental new positions1. **Never commit `.env` file** to version control

- Waits for all positions to close before exiting2. **Use separate API keys** for production and testing

3. **Start with small amounts** to test the bot

### Error Handling4. **Monitor the bot** regularly, especially initially

5. **Set MAX_TRADES limit** when testing

If an error occurs:6. **Use testnet first** before mainnet deployment

1. Check the terminal output for error messages

2. Verify your `.env` configuration## 🧪 Testing

3. Ensure both accounts have sufficient balance

4. Check that private keys match account indices### Test on Lighter Testnet



## 🛠️ Troubleshooting1. Get testnet accounts from Lighter

2. Fund both accounts with testnet tokens

### "Invalid nonce" errors3. Configure `.env` with testnet credentials

- This is solved by the multi-process architecture4. Set `BASE_URL=https://testnet.zklighter.elliot.ai`

- Each worker has its own isolated signer5. Start with small `BASE_AMOUNT`

6. Set `MAX_TRADES=5` for limited testing

### "Account not found" errors

- Verify ACCOUNT1_INDEX and ACCOUNT2_INDEX match your actual account indices### Example Test Configuration

- Check that private keys correspond to these accounts

```env

### Position closing failsBASE_URL=https://testnet.zklighter.elliot.ai

- The bot now uses `reduce_only=True` which is safeBASE_AMOUNT=10000          # 0.001 ETH for testing

- If closing still fails, the position may have already been closed manuallyMAX_SLIPPAGE=0.05          # 5% for testnet

INTERVAL_SECONDS=120       # 2 minutes

### SDK errorsMAX_TRADES=10              # Limit to 10 trades

- Ensure lighter-python is installed: `pip install -e .\lighter-python````

- Check that virtual environment is activated

## 📈 Monitoring and Logs

## 📝 License

### Log Files

This project is for educational and testing purposes. Use at your own risk.

- `delta_neutral_bot.log`: Main log file (inside container)

## 🤝 Contributing- Console output: Real-time logs via `docker-compose logs -f`



This bot is designed for the Lighter DEX testnet. Always test thoroughly before any mainnet use.### Log Locations



## 📞 Support```bash

# View logs in container

For issues or questions about Lighter DEX:docker-compose exec delta-neutral-bot cat delta_neutral_bot.log

- Discord: https://discord.gg/lighter

- Documentation: https://docs.lighter.xyz/# Copy logs to host

mkdir -p logs

---docker cp lighter-delta-neutral-bot:/app/delta_neutral_bot.log ./logs/

```

**⚠️ DISCLAIMER**: This bot involves financial transactions. Always test on testnet first. Never use more funds than you can afford to lose. The authors are not responsible for any financial losses.

### What to Monitor

- **Success Rate**: Percentage of successful trades
- **Execution Prices**: Compare with expected prices
- **Slippage**: Actual vs maximum allowed
- **Error Messages**: Connection or execution errors
- **Account Balances**: Ensure sufficient funds

## ❌ Troubleshooting

### Bot Won't Start

```bash
# Check logs
docker-compose logs

# Verify environment variables
docker-compose config

# Rebuild image
docker-compose build --no-cache
docker-compose up
```

### Connection Errors

- Verify `BASE_URL` is correct
- Check internet connectivity
- Ensure API keys are valid
- Verify account indices are correct

### Trade Execution Failures

- Check account balances
- Verify market is active
- Reduce `BASE_AMOUNT` if insufficient balance
- Increase `MAX_SLIPPAGE` if price moves too fast
- Check for rate limiting

### Docker Issues

```bash
# Remove all containers and images
docker-compose down -v
docker system prune -a

# Rebuild from scratch
docker-compose build --no-cache
docker-compose up
```

## 🛠️ Development

### Local Testing (without Docker)

**Note**: The Lighter SDK doesn't support Windows directly. Use Docker or WSL2.

```bash
# Install dependencies
pip install -r requirements.txt

# Install Lighter SDK
cd lighter-python/.others
pip install -e .
cd ../..

# Set environment variables
export ACCOUNT1_PRIVATE_KEY="..."
export ACCOUNT1_INDEX="1"
# ... (set all required variables)

# Run the bot
python delta_neutral_bot.py
```

### Using WSL2 on Windows

```bash
# In WSL2 terminal
cd /mnt/e/"Volume Generation Bot"
python delta_neutral_bot.py
```

## 📝 Advanced Configuration

### Batch Mode

Enable batch transactions for better atomicity:

```env
USE_BATCH_MODE=true
```

Note: Batch mode signs transactions before sending, allowing for better nonce management.

### Custom Market

Trade different markets by changing the market index:

```env
MARKET_INDEX=1  # Different market
```

Check Lighter documentation for available markets.

### Rate Limiting

Adjust interval to avoid rate limits:

```env
INTERVAL_SECONDS=300  # 5 minutes between trades
```

## 🤝 Support

For issues related to:
- **Lighter API**: Check official Lighter documentation
- **This Bot**: Review logs and configuration
- **Docker**: Ensure Docker is properly installed

## ⚠️ Disclaimer

This bot is for educational and volume generation purposes. Use at your own risk:

- **No Guarantees**: Trading involves risk
- **Test First**: Always test on testnet
- **Monitor Closely**: Don't leave unattended
- **Check Regulations**: Ensure compliance with local laws

## 📜 License

This project is provided as-is for educational purposes.

---

**Happy Trading! 🚀**

#!/usr/bin/env python3
"""
Analyze trading losses to identify bleeding causes
"""
import pandas as pd
import numpy as np

# Load both CSVs
df1 = pd.read_csv('lighter-trade-export-1.csv')
df2 = pd.read_csv('lighter-trade-export-2.csv')

# Get last 259 trades (518 rows = 259 pairs of open/close)
df1_recent = df1.head(518).copy()
df2_recent = df2.head(518).copy()

# Convert PnL to numeric
df1_recent['PnL'] = pd.to_numeric(df1_recent['Closed PnL'].replace('-', np.nan), errors='coerce').fillna(0)
df2_recent['PnL'] = pd.to_numeric(df2_recent['Closed PnL'].replace('-', np.nan), errors='coerce').fillna(0)

print('='*70)
print('BLEEDING ANALYSIS - Last 259 Trades')
print('='*70)

print('\n=== OVERALL PNL ===')
acc1_pnl = df1_recent['PnL'].sum()
acc2_pnl = df2_recent['PnL'].sum()
total_pnl = acc1_pnl + acc2_pnl
print(f'Account 1 (Long):  ${acc1_pnl:.4f}')
print(f'Account 2 (Short): ${acc2_pnl:.4f}')
print(f'Combined Loss:     ${total_pnl:.4f}')
print(f'Loss as % of $120: {(abs(total_pnl)/120)*100:.2f}%')

print('\n=== WIN/LOSS RATIO ===')
acc1_losses = (df1_recent['PnL'] < 0).sum()
acc1_wins = (df1_recent['PnL'] > 0).sum()
acc2_losses = (df2_recent['PnL'] < 0).sum()
acc2_wins = (df2_recent['PnL'] > 0).sum()

print(f'Account 1: {acc1_wins} wins, {acc1_losses} losses ({(acc1_losses/(acc1_wins+acc1_losses))*100:.1f}% loss rate)')
print(f'Account 2: {acc2_wins} wins, {acc2_losses} losses ({(acc2_losses/(acc2_wins+acc2_losses))*100:.1f}% loss rate)')

# Analyze paired trades
print('\n=== PAIRED TRADE ANALYSIS ===')
pairs = []
for i in range(0, min(len(df1_recent), len(df2_recent)), 2):
    if i+1 >= len(df1_recent) or i+1 >= len(df2_recent):
        break
    
    open1 = df1_recent.iloc[i+1]
    close1 = df1_recent.iloc[i]
    open2 = df2_recent.iloc[i+1]
    close2 = df2_recent.iloc[i]
    
    # Verify this is a valid pair
    if ('Open' in str(open1['Side']) and 'Close' in str(close1['Side']) and 
        'Open' in str(open2['Side']) and 'Close' in str(close2['Side']) and
        open1['Market'] == open2['Market']):
        
        long_open_price = float(open1['Price'])
        long_close_price = float(close1['Price'])
        short_open_price = float(open2['Price'])
        short_close_price = float(close2['Price'])
        
        # Calculate spreads
        spread_open = abs(long_open_price - short_open_price)
        spread_close = abs(long_close_price - short_close_price)
        avg_price = (long_open_price + short_open_price) / 2
        spread_open_pct = (spread_open / avg_price) * 100
        
        # Slippage analysis
        # For delta neutral: we pay spread twice (once on open, once on close)
        total_spread_cost = spread_open + spread_close
        spread_cost_pct = (total_spread_cost / avg_price) * 100
        
        pair_pnl = close1['PnL'] + close2['PnL']
        
        pairs.append({
            'market': open1['Market'],
            'spread_open': spread_open,
            'spread_open_pct': spread_open_pct,
            'spread_close': spread_close,
            'spread_cost_pct': spread_cost_pct,
            'pair_pnl': pair_pnl,
            'long_pnl': close1['PnL'],
            'short_pnl': close2['PnL']
        })

df_pairs = pd.DataFrame(pairs)

print(f'Total trade pairs analyzed: {len(df_pairs)}')
print(f'Average pair PnL: ${df_pairs["pair_pnl"].mean():.6f}')
print(f'Median pair PnL: ${df_pairs["pair_pnl"].median():.6f}')
print(f'Losing pairs: {(df_pairs["pair_pnl"] < 0).sum()} ({(df_pairs["pair_pnl"] < 0).sum()/len(df_pairs)*100:.1f}%)')

print('\n=== SPREAD ANALYSIS (Root Cause) ===')
print(f'Average opening spread: {df_pairs["spread_open_pct"].mean():.4f}%')
print(f'Median opening spread: {df_pairs["spread_open_pct"].median():.4f}%')
print(f'Max opening spread: {df_pairs["spread_open_pct"].max():.4f}%')
print(f'Average total spread cost: {df_pairs["spread_cost_pct"].mean():.4f}%')

print('\n=== BY MARKET ===')
for market in sorted(df_pairs['market'].unique()):
    m_data = df_pairs[df_pairs['market'] == market]
    print(f'{market:8s}: {len(m_data):3d} pairs | Avg PnL: ${m_data["pair_pnl"].mean():8.5f} | '
          f'Avg Spread: {m_data["spread_open_pct"].mean():.4f}% | '
          f'Loss Rate: {(m_data["pair_pnl"] < 0).sum()/len(m_data)*100:.0f}%')

print('\n=== WORST MARKETS (Most Bleeding) ===')
market_summary = df_pairs.groupby('market').agg({
    'pair_pnl': ['sum', 'mean', 'count'],
    'spread_open_pct': 'mean'
}).round(6)
market_summary.columns = ['Total PnL', 'Avg PnL', 'Trades', 'Avg Spread %']
market_summary = market_summary.sort_values('Total PnL')
print(market_summary.head(5))

print('\n=== KEY FINDINGS ===')
avg_loss_per_pair = df_pairs["pair_pnl"].mean()
expected_loss_from_spread = df_pairs["spread_cost_pct"].mean()
print(f'1. Average loss per trade pair: ${avg_loss_per_pair:.6f}')
print(f'2. Average spread cost: {expected_loss_from_spread:.4f}%')
print(f'3. For $40 notional (2*$2 @ 10x), {expected_loss_from_spread:.4f}% = ${(40 * expected_loss_from_spread/100):.6f}')
print(f'4. Win rate is too low: {(df_pairs["pair_pnl"] > 0).sum()}/{len(df_pairs)} = {(df_pairs["pair_pnl"] > 0).sum()/len(df_pairs)*100:.1f}%')

# Check if dynamic leverage correlates with worse outcomes
print('\n=== RECOMMENDATIONS ===')
if expected_loss_from_spread > 0.02:
    print('⚠️  Opening spreads are TOO HIGH (>0.02%)')
    print('   Solution: Tighten MAX_SPREAD check or trade more liquid markets')
if avg_loss_per_pair < -0.01:
    print('⚠️  Average pair loss is significant')
    print('   Solution: Reduce trading frequency or increase position hold time')
if (df_pairs["pair_pnl"] < 0).sum() / len(df_pairs) > 0.6:
    print('⚠️  Loss rate > 60% indicates systematic issue')
    print('   Solution: Market orders are crossing spread twice per cycle')

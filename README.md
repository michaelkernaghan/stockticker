# Stock Ticker (Desktop)

A simple desktop implementation of the classic 1937 board game Stock Ticker.

- Desktop UI: Tkinter
- Language: Python 3.10+

## How to run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
python app.py
```

If your system uses `python` instead of `python3`, adjust accordingly.

## Gameplay summary (per rules)

- Six stocks: Gold, Silver, Bonds, Oil, Industrials, Grain.
- Each stock starts at $1.00. Dice determine: which stock, Up/Down/Dividend, and the amount (5¢, 10¢, 20¢).
- Dividends only pay when the stock is at or above $1.00 and pay a flat cents/share equal to the die (5/10/20), irrespective of price.
- Split: when a stock hits $2.00, holders' shares double and price resets to $1.00.
- Bankrupt: when a stock hits $0.00, holders lose their shares; price resets to $1.00.
- Players begin with $5000 and may trade in blocks of 500/1000/2000/5000 shares.

This app opens trading after every roll for simplicity. End trading to roll again.

## References

- Rules PDF included in `pdf/stocktickerrules.pdf`. Original gameplay description summarized from Wikipedia.
  - Wikipedia: https://en.wikipedia.org/wiki/Stock_Ticker
  - Tabletop Simulator workshop reference: https://steamcommunity.com/sharedfiles/filedetails/?id=2002912644

## Save/load

Not yet exposed in UI, but the engine supports JSON serialization in `GameState.to_json()` / `from_json()`.

## Notes

- This is a simple local hotseat implementation for quick play and testing. No network play.
- Contributions welcome.

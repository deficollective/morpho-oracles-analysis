# Morpho Oracles analysis

This repository holds scripts to analyse the oracles used within morpho markets.

## Usage

In order to reproduce the result you need to add an RPC URL, compute a fresh TVL analysis on TheGraph, and then either run all action at once by running `py oracles.py` or run each action individually:

1.  Run `py oracles.py --oracles` to retrieve all markets and oracles addresses
2.  Run `py oracles.py --aggr` to retrieve the price aggregation feeds used in the oracles
3.  Run `py oracles.py --analysis` to analyse the result and match the TVL with markets.

Final results are saved in `analysis.json.

## Last Results (25th March 2025)

We ran the script on the 25th of March and obtained the following results:

```
{
    "total_tvl_usd": 2231661274.4441214,
    "chainlink_tvl_usd": 688731754.910966,
    "tvl_percentage": 30.861841032865545,
    "total_markets": 466,
    "chainlink_markets": 173,
    "market_percentage": 37.1244635193133,
}
```

Which can be interpreted to say that 30.80% of the TVL in Morpho markets relies on chainlink oracles. This represents 176 markets holding $688.73 Mio out of the 466 total markets created on Morpho ($2.231 Bio TVL in total).

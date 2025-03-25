# Morpho Oracles analysis

This repository holds scripts to analyse the oracles used within morpho markets.

## Usage

In order to reproduce the result you need to add an RPC URL, and then either run all action at once by running `py oracles.py` or run each action individually:

1.  Run `py oracles.py --oracles` to retrieve all markets and oracles addresses
2.  Run `py oracles.py --aggr` to retrieve the price aggregation feeds used in the oracles
3.  Run `py oracles.py --analysis` to analyse the result and match the TVL with markets.

Final results are saved in `analysis.json.

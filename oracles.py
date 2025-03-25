import json
import argparse
from web3 import Web3
import eth_abi
with open("oracle_abi.json", "r") as abi_file:
    oracel_abi = json.load(abi_file)

with open("morpho_abi.json", "r") as abi_file:
    morpho_abi = json.load(abi_file)


# Connect to Ethereum node (Infura, Alchemy, or self-hosted node)
RPC_URL = "https://mainnet.infura.io/v3/YOU-API-KEY"
w3 = Web3(Web3.HTTPProvider(RPC_URL))

# Contract address and event signature
CONTRACT_ADDRESS = "0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb"
EVENT_SIGNATURE = "0xac4b2400f169220b0c0afdde7a0b32e775ba727ea1cb30b35f935cdaab8683ac"

# Oracle function names
ORACLE_FUNCTIONS = ["BASE_FEED_1", "BASE_FEED_2",
                    "QUOTE_FEED_1", "QUOTE_FEED_2"]


def fetch_create_market_events():
    latest_block = w3.eth.block_number
    from_block = 0  # Adjust based on contract deployment block

    markets = list()

    logs = w3.eth.get_logs({
        "fromBlock": from_block,
        "toBlock": latest_block,
        "address": CONTRACT_ADDRESS,
        "topics": [EVENT_SIGNATURE]
    })

    morpho = w3.eth.contract(
        address=Web3.to_checksum_address(CONTRACT_ADDRESS), abi=morpho_abi)

    for log in logs:
        data_bytes = log["data"][:]  # Remove '0x' prefix
        if len(data_bytes) < 160:
            continue  # Skip malformed events

        id = eth_abi.decode(["bytes32"], log["topics"][1])[0]
        oracle_address = eth_abi.decode(["address"], data_bytes[64:96])[0]

        try:
            market_params = morpho.functions.market(id).call()
        except Exception as e:
            print(f"couldn't query market: {e}")

        markets.append(
            {"id": Web3.to_hex(id), "oracle": oracle_address, "market": market_params})
    return markets


def save_json(data, filename):
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)


def query_aggregators():
    with open("markets.json", "r") as f:
        markets = json.load(f)

    aggregators = {}
    for oracle in set(market["oracle"] for market in markets):
        oracle_contract = w3.eth.contract(
            address=Web3.to_checksum_address(oracle), abi=oracel_abi)

        found = False
        for func in ORACLE_FUNCTIONS:
            try:
                addr = oracle_contract.functions[func]().call()
                if addr != "0x0000000000000000000000000000000000000000":
                    found = True
                    aggregators.setdefault(oracle, {})[func] = addr
            except Exception as e:
                print(f"Skipping {func} for {oracle}: {e}")
        if not found:
            aggregators.setdefault(oracle, {})["DEFAULT"] = oracle

    save_json(aggregators, "aggregator.json")
    print(f"Saved {len(aggregators)} aggregators to aggregator.json")


def analyze_tvl():
    try:
        # Load markets data
        with open("markets.json", "r") as f:
            markets = json.load(f)

        # Load TVL data - This comes from TheGraph:
        # https://thegraph.com/explorer/subgraphs/8Lz789DP5VKLXumTMTgygjU2xtuzx8AhbaacgN5PYCAs?view=Query&chain=arbitrum-one
        # Query:
        # {
        #  markets(orderBy: totalValueLockedUSD, orderDirection: desc) {
        #    id
        #    totalValueLockedUSD
        #  }
        # }
        with open("tvl.json", "r") as f:
            tvl_data = json.load(f)

        # Load aggregators data
        with open("aggregator.json", "r") as f:
            aggregators = json.load(f)

        # Load chainlink addresses
        with open("chainlink.json", "r") as f:
            chainlink_data = json.load(f)
            chainlink_addresses = chainlink_data["addresses"]
    except Exception as e:
        print(f"Couldn't load data: {e}")
        return

    # Create a mapping of market IDs to TVL values
    tvl_map = {}
    for market_tvl in tvl_data["data"]["markets"]:
        tvl_map[market_tvl["id"]] = float(market_tvl["totalValueLockedUSD"])

    # Create a copy of tvl_map to track unused markets
    unused_markets = tvl_map.copy()

    total_tvl = 0
    chainlink_tvl = 0
    total_markets = len(markets)
    chainlink_markets = 0
    processed_market_ids = set()
    for market in markets:
        # Extract TVL from tvl.json using market ID
        market_id = market["id"]
        processed_market_ids.add(market_id)

        market_tvl = tvl_map.get(market_id, 0)
        if market_id in unused_markets:
            del unused_markets[market_id]  # Remove from unused markets

        total_tvl += market_tvl

        # Check if this market's oracle uses a Chainlink aggregator
        oracle_address = market["oracle"]
        oracle_uses_chainlink = False

        # Check if the oracle address is in aggregators
        if oracle_address in aggregators:
            # Check if any of the feeds are in the chainlink list
            for feed_name, feed_address in aggregators[oracle_address].items():
                if feed_address in chainlink_addresses:
                    oracle_uses_chainlink = True
                    break

        if oracle_uses_chainlink:
            chainlink_tvl += market_tvl
            chainlink_markets += 1

    tvl_percentage = (chainlink_tvl / total_tvl * 100) if total_tvl > 0 else 0
    market_percentage = (chainlink_markets / total_markets *
                         100) if total_markets > 0 else 0

    # Calculate unused TVL
    unused_tvl = sum(unused_markets.values())
    unused_market_count = len(unused_markets)

    print(f"Total TVL: ${total_tvl:,.2f} USD")
    print(
        f"TVL using Chainlink: ${chainlink_tvl:,.2f} USD ({tvl_percentage:.2f}%)")
    print(f"Total Markets: {total_markets}")
    print(
        f"Markets using Chainlink: {chainlink_markets} ({market_percentage:.2f}%)")
    print(
        f"\nUnused Markets (in tvl.json but not processed): {unused_market_count}")
    print(f"Unused TVL: ${unused_tvl:,.2f} USD")

    # Show top 5 unused markets by TVL
    if unused_markets:
        print("\nTop 5 unused markets by TVL:")
        sorted_unused = sorted(unused_markets.items(),
                               key=lambda x: x[1], reverse=True)
        for i, (market_id, tvl) in enumerate(sorted_unused[:5]):
            print(f"{i+1}. ID: {market_id} - TVL: ${tvl:,.2f} USD")

    # Save analysis results
    analysis_results = {
        "total_tvl_usd": total_tvl,
        "chainlink_tvl_usd": chainlink_tvl,
        "tvl_percentage": float(tvl_percentage),
        "total_markets": total_markets,
        "chainlink_markets": chainlink_markets,
        "market_percentage": float(market_percentage),
        "unused_markets_count": unused_market_count,
        "unused_tvl_usd": unused_tvl,
        "unused_market_ids": list(unused_markets.keys())
    }
    save_json(analysis_results, "analysis.json")
    print(f"\nAnalysis results saved to analysis.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--aggr", action="store_true",
                        help="Query aggregator addresses from oracles.json")
    parser.add_argument("--analysis", action="store_true",
                        help="Analyze TVL and usage of Chainlink aggregators")
    parser.add_argument("--oracles", action="store_true",
                        help="Analyze markets and oracles created on Morpho")
    args = parser.parse_args()

    if args.aggr:
        query_aggregators()
    elif args.analysis:
        analyze_tvl()
    elif args.oracles:
        oracles = fetch_create_market_events()
        save_json(oracles, "markets.json")
        print(f"Saved {len(oracles)} markets to markets.json")
    else:
        print(f"Starting analysis, retrieving oracles...")
        oracles = fetch_create_market_events()
        save_json(oracles, "markets.json")
        print(f"Saved {len(oracles)} markets to markets.json")

        print(f"Retrieving price feeds...")
        query_aggregators()

        analyze_tvl()

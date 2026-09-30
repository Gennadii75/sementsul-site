import json, urllib.request, datetime

CONTRACT = "0xF79C02a681b3237C7c49D9a6D16BB97316518Ef3"
OUT = "data/price.json"

def get(url, timeout=20):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read().decode())

def main():
    price_usd = None
    price_native = None
    pair_url = None
    liquidity_usd = None
    change_24h = None
    try:
        dex = get(f"https://api.dexscreener.com/latest/dex/tokens/{CONTRACT}")
        pairs = dex.get("pairs") or []
        bsc_pairs = [p for p in pairs if p.get("chainId") == "bsc"] or pairs
        if bsc_pairs:
            p0 = sorted(bsc_pairs, key=lambda p: float(p.get("liquidity", {}).get("usd") or 0), reverse=True)[0]
            price_usd = p0.get("priceUsd")
            price_native = p0.get("priceNative")
            pair_url = p0.get("url")
            liquidity_usd = (p0.get("liquidity") or {}).get("usd")
            change_24h = (p0.get("priceChange") or {}).get("h24")
    except Exception as e:
        print("dexscreener error:", e)

    bnb_usd = None
    try:
        cg = get("https://api.coingecko.com/api/v3/simple/price?ids=binancecoin&vs_currencies=usd")
        bnb_usd = cg.get("binancecoin", {}).get("usd")
    except Exception as e:
        print("coingecko error:", e)

    total_supply = "1000000000"
    try:
        payload = json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": "eth_call",
            "params": [{"to": CONTRACT, "data": "0x18160ddd"}, "latest"]
        }).encode()
        req = urllib.request.Request("https://bsc-dataseed.binance.org",
                                     data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=20) as r:
            res = json.loads(r.read().decode())
        total_supply = str(int(res.get("result", "0x0"), 16) / 10**18)
    except Exception as e:
        print("bsc rpc error:", e)

    data = {
        "priceUsd": price_usd,
        "priceNative": price_native,
        "liquidityUsd": liquidity_usd,
        "change24h": change_24h,
        "bnbUsd": bnb_usd,
        "totalSupply": total_supply,
        "pairUrl": pair_url,
        "updatedAt": datetime.datetime.utcnow().isoformat() + "Z",
        "contract": CONTRACT,
    }
    with open(OUT, "w") as f:
        json.dump(data, f, indent=2)
    print("wrote", OUT, data)

if __name__ == "__main__":
    main()


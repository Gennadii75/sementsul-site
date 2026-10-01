import json, os, urllib.request, datetime

CONTRACT = "0xF79C02a681b3237C7c49D9a6D16BB97316518Ef3"
OUT = "data/price.json"

def get(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (SML price updater)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())

def main():
    price_usd = None
    price_native = None
    pair_url = None
    liquidity_usd = None
    change_24h = None
    try:
        gt = get(f"https://api.geckoterminal.com/api/v2/networks/bsc/tokens/{CONTRACT}/pools?page=1")
        pools = gt.get("data") or []
        if pools:
            a0 = sorted(pools, key=lambda p: float((p.get("attributes") or {}).get("reserve_in_usd") or 0), reverse=True)[0]
            attr = a0.get("attributes") or {}
            price_usd = attr.get("base_token_price_usd")
            liquidity_usd = attr.get("reserve_in_usd")
            change_24h = (attr.get("price_change_percentage") or {}).get("h24")
            pool_addr = attr.get("address")
            if pool_addr:
                pair_url = f"https://www.geckoterminal.com/bsc/pools/{pool_addr}"
    except Exception as e:
        print("geckoterminal error:", e)
    except Exception as e:
        print("dexscreener error:", e)

    bnb_usd = None
    try:
        cg = get("https://api.coingecko.com/api/v3/simple/price?ids=binancecoin&vs_currencies=usd")
        bnb_usd = cg.get("binancecoin", {}).get("usd")
    except Exception as e:
        print("coingecko error:", e)

    holders = None
    api_key = os.environ.get("BSCSCAN_API_KEY")
    if api_key:
        try:
            bsc = get(f"https://api.etherscan.io/v2/api?chainid=56&module=token&action=tokenholderlist&contractaddress={CONTRACT}&page=1&offset=10000&apikey={api_key}")
            if str(bsc.get("status")) == "1":
                holders = len(bsc.get("result") or [])
            else:
                print("bscscan holders:", bsc.get("message"), bsc.get("result"))
        except Exception as e:
            print("bscscan error:", e)

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
        "holders": holders,
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


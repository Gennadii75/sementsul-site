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
    moralis_key = os.environ.get("MORALIS_API_KEY")
    if moralis_key:
        # Moralis Token Owners (free-план): пагинация курсором, считаем владельцев.
        try:
            import urllib.parse
            total = 0
            cursor = ""
            for _ in range(10):
                url = f"https://deep-index.moralis.io/api/v2.2/erc20/{CONTRACT}/owners?chain=bsc&order=DESC&limit=100" + (f"&cursor={urllib.parse.quote(cursor)}" if cursor else "")
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (SML price updater)", "X-API-Key": moralis_key})
                with urllib.request.urlopen(req, timeout=20) as r:
                    owners = json.loads(r.read().decode())
                result = owners.get("result") or []
                total += len(result)
                cursor = owners.get("cursor") or ""
                if not cursor or not result:
                    break
            else:
                print("moralis owners: more than 1000 holders, count capped")
            holders = total or None
        except Exception as e:
            print("moralis error:", e)
    elif api_key:
        # Бесплатный способ: все переводы токена (tokentx входит в free-план),
        # считаем адреса с положительным балансом. tokenholderlist — платный.
        try:
            balances = {}
            page = 1
            while page <= 5:
                tx = get(f"https://api.etherscan.io/v2/api?chainid=56&module=account&action=tokentx&contractaddress={CONTRACT}&page={page}&offset=10000&startblock=0&endblock=99999999&sort=asc&apikey={api_key}")
                if str(tx.get("status")) != "1":
                    print("bscscan tx:", tx.get("message"), str(tx.get("result"))[:200])
                    break
                result = tx.get("result") or []
                if not result:
                    break
                for t in result:
                    try:
                        val = int(t.get("value", "0"))
                    except (TypeError, ValueError):
                        continue
                    f = (t.get("from") or "").lower()
                    to = (t.get("to") or "").lower()
                    if f and f != "0x0000000000000000000000000000000000000000":
                        balances[f] = balances.get(f, 0) - val
                    if to and to != "0x0000000000000000000000000000000000000000":
                        balances[to] = balances.get(to, 0) + val
                if len(result) < 10000:
                    break
                page += 1
            else:
                print("bscscan tx: too many transfers, holder count capped")
            if balances:
                holders = sum(1 for v in balances.values() if v > 0)
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


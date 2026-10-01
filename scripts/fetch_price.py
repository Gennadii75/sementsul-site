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
    # Способ 1 (бесплатно, без ключа): все Transfer-логи с публичного RPC,
    # считаем адреса с положительным балансом.
    try:
        transfer_topic = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
        payload = json.dumps({"jsonrpc": "2.0", "id": 2, "method": "eth_blockNumber", "params": []}).encode()
        req = urllib.request.Request("https://bsc-dataseed.binance.org", data=payload, headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 (SML price updater)"})
        with urllib.request.urlopen(req, timeout=20) as r:
            latest = int(json.loads(r.read().decode()).get("result", "0x0"), 16)
        deploy_block = 124978800
        balances = {}
        step = 500000
        start = deploy_block
        while start <= latest:
            end = min(start + step - 1, latest)
            payload = json.dumps({
                "jsonrpc": "2.0", "id": 3, "method": "eth_getLogs",
                "params": [{"address": CONTRACT, "topics": [transfer_topic],
                            "fromBlock": hex(start), "toBlock": hex(end)}]
            }).encode()
            req = urllib.request.Request("https://bsc-dataseed.binance.org", data=payload, headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 (SML price updater)"})
            with urllib.request.urlopen(req, timeout=30) as r:
                logs = json.loads(r.read().decode()).get("result") or []
            for lg in logs:
                topics = lg.get("topics") or []
                if len(topics) < 3:
                    continue
                f = "0x" + topics[1][-40:]
                to = "0x" + topics[2][-40:]
                try:
                    val = int(lg.get("data", "0x0"), 16)
                except (TypeError, ValueError):
                    continue
                zero = "0x0000000000000000000000000000000000000000"
                if f.lower() != zero:
                    balances[f.lower()] = balances.get(f.lower(), 0) - val
                if to.lower() != zero:
                    balances[to.lower()] = balances.get(to.lower(), 0) + val
            start = end + 1
        holders = sum(1 for v in balances.values() if v > 0) or None
    except Exception as e:
        print("rpc holders error:", e)
    if holders is None and api_key:
        # Запасной вариант (для BSC тоже может требовать платный план).
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


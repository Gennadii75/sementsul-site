"""Daily SML analytics post to Telegram channel. Reads data/price.json."""
import json
import os
import urllib.request
import urllib.parse

PRICE_FILE = "data/price.json"
CONTRACT = "0xF79C02a681b3237C7c49D9a6D16BB97316518Ef3"


def fmt_usd(n):
    if n is None:
        return "—"
    try:
        v = float(n)
    except (TypeError, ValueError):
        return "—"
    if v >= 1000:
        return "$" + f"{v:,.0f}"
    if v >= 1:
        return f"${v:.2f}"
    return f"${v:.3g}"


def fmt_int(n):
    try:
        return f"{int(float(n)):,}".replace(",", " ")
    except (TypeError, ValueError):
        return "—"


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        raise SystemExit("TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID are not set")

    with open(PRICE_FILE, encoding="utf-8") as f:
        d = json.load(f)

    price = fmt_usd(d.get("priceUsd"))
    liq = fmt_usd(d.get("liquidityUsd"))
    holders = fmt_int(d.get("holders")) if d.get("holders") is not None else "—"
    supply = fmt_int(d.get("totalSupply"))
    change = d.get("change24h")
    change_s = ""
    if change is not None:
        try:
            c = float(change)
            change_s = f" ({'+' if c >= 0 else ''}{c:.2f}% 24ч)"
        except (TypeError, ValueError):
            pass

    text = (
        "⚜️ <b>Sementsul (SML) — дневной отчет</b>\n\n"
        f"💰 Цена: <b>{price}</b>{change_s}\n"
        f"🏦 Ликвидность: <b>{liq}</b>\n"
        f"👑 Держатели: <b>{holders}</b>\n"
        f"📦 Эмиссия: <b>{supply}</b>\n\n"
        f"🌐 <a href=\"https://sementsul.net/\">Сайт</a> | "
        f"<a href=\"https://pancakeswap.finance/swap?outputCurrency={CONTRACT}\">Купить</a> | "
        f"<a href=\"https://bscscan.com/token/{CONTRACT}\">BscScan</a>"
    )

    payload = urllib.parse.urlencode({
        "chat_id": chat,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded",
                 "User-Agent": "Mozilla/5.0 (SML reporter)"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        res = json.loads(r.read().decode())
    if not res.get("ok"):
        raise SystemExit(f"telegram error: {res}")
    print("posted:", res["result"]["message_id"])


if __name__ == "__main__":
    main()

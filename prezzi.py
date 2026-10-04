import os, json, urllib.request, urllib.error, time, datetime
T = os.environ["CARDTRADER_TOKEN"]
B = "https://api.cardtrader.com/api/v2"
EXPS = {"OP01": 3332, "OP17": 4769}
LANGS = ["en", "jp", "zh-CN"]
OK_COND = {"Mint", "Near Mint"}

def get(path):
    r = urllib.request.Request(B + path, headers={"Authorization": "Bearer " + T})
    for i in range(3):
        try:
            with urllib.request.urlopen(r, timeout=120) as x:
                return json.load(x)
        except urllib.error.HTTPError as e:
            if e.code == 429 and i < 2:
                time.sleep(5); continue
            print("ERRORE", e.code, path, e.read()[:300]); raise SystemExit(1)

out = {"updated": datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z",
       "currency": "EUR", "cards": []}
for code, eid in EXPS.items():
    bps = get("/blueprints/export?expansion_id=%d" % eid)
    prods = get("/marketplace/products?expansion_id=%d" % eid)
    for b in bps:
        fp = b.get("fixed_properties") or {}
        cn = fp.get("collector_number")
        if not cn:
            continue
        prices = {}
        lst = prods.get(str(b["id"]), []) if isinstance(prods, dict) else []
        for p in lst:
            h = p.get("properties_hash") or {}
            if h.get("graded") or h.get("signed") or h.get("altered"):
                continue
            if h.get("condition") not in OK_COND:
                continue
            lang = h.get("onepiece_language")
            c = p.get("price_cents")
            if lang not in LANGS or c is None or p.get("price_currency") != "EUR":
                continue
            d = prices.setdefault(lang, {"min": None, "n": 0})
            d["n"] += p.get("quantity") or 1
            if d["min"] is None or c < d["min"]:
                d["min"] = c
        for d in prices.values():
            d["min"] = round(d["min"] / 100, 2)
        out["cards"].append({"exp": code, "bp": b["id"], "code": cn, "name": b.get("name"),
                             "version": b.get("version"), "rarity": fp.get("onepiece_rarity"),
                             "cardmarket_ids": b.get("card_market_ids"), "prices": prices})
json.dump(out, open("prices.json", "w"), ensure_ascii=False, indent=1)
print("Carte salvate:", len(out["cards"]), "- con almeno un prezzo:",
      sum(1 for c in out["cards"] if c["prices"]))

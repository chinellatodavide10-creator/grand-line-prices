import os, json, urllib.request, urllib.error, time, datetime, re
from collections import Counter

T = os.environ["CARDTRADER_TOKEN"]
B = "https://api.cardtrader.com/api/v2"
CM_BASE = "https://downloads.s3.cardmarket.com/productCatalog/"
CM_GAME = 18  # One Piece su Cardmarket
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
                time.sleep(5)
                continue
            print("ERRORE", e.code, path, e.read()[:300])
            raise SystemExit(1)


def cm_get(path):
    r = urllib.request.Request(CM_BASE + path, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(r, timeout=180) as x:
        return json.load(x)


def slug(t):
    return re.sub(r"[^a-z0-9]+", "-", (t or "").lower()).strip("-")


def load(path, default):
    try:
        return json.load(open(path))
    except Exception:
        return default


now = datetime.datetime.now(datetime.timezone.utc)
stamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")
today = now.strftime("%Y-%m-%d")

# --- Cardmarket: listino ufficiale pubblico (aggiornato una volta al giorno) ---
prev = load("prezzi_latest.json", {})
try:
    guide = cm_get("priceGuide/price_guide_%d.json" % CM_GAME)
    plist = cm_get("productList/products_singles_%d.json" % CM_GAME)
    G = {g["idProduct"]: g for g in guide.get("priceGuides", [])}
    EXP = {p["idProduct"]: p.get("idExpansion") for p in plist.get("products", [])}
    cm_date = guide.get("createdAt")
    cm_ok = True
except Exception as e:
    print("Cardmarket non raggiungibile, uso i dati precedenti:", str(e)[:100])
    G, EXP, cm_date, cm_ok = {}, {}, prev.get("cmDate"), False

# --- CardTrader ---
cards = []
for code, eid in EXPS.items():
    bps = get("/blueprints/export?expansion_id=%d" % eid)
    prods = get("/marketplace/products?expansion_id=%d" % eid)
    pairs = Counter()
    for b in bps:
        ids = b.get("card_market_ids") or []
        if len(ids) >= 2 and ids[0] in EXP and ids[1] in EXP:
            pairs[(EXP[ids[0]], EXP[ids[1]])] += 1
    en_exp, jp_exp = pairs.most_common(1)[0][0] if pairs else (None, None)
    for b in bps:
        fp = b.get("fixed_properties") or {}
        cn = fp.get("collector_number")
        if not cn:
            continue
        best = {}
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
            if lang not in best or c < best[lang]:
                best[lang] = c
        arr = [round(best[l] / 100, 2) if l in best else None for l in LANGS]
        # prodotti Cardmarket: primo id = edizione inglese, secondo = edizione giapponese
        ids = b.get("card_market_ids") or []
        en = jp = None
        if len(ids) >= 2:
            en, jp = ids[0], ids[1]
        elif len(ids) == 1:
            e = EXP.get(ids[0])
            if e is not None and e == en_exp:
                en = ids[0]
            elif e is not None and e == jp_exp:
                jp = ids[0]

        def pr(i):
            g = G.get(i) if i else None
            if not g:
                return None, None
            return (g.get("trend") or None), (g.get("low") or None)

        et, el = pr(en)
        jt, jl = pr(jp)
        cards.append((cn, b.get("version"), arr, [et, el, jt, jl], [en, jp]))

cnt = {}
for cn, _, _, _, _ in cards:
    cnt[cn] = cnt.get(cn, 0) + 1
latest, cm, ci = {}, {}, {}
for cn, ver, arr, v, ids in cards:
    k = cn if cnt[cn] == 1 else cn + "~" + slug(ver)
    if any(x is not None for x in arr):
        latest[k] = arr
    if any(x is not None for x in v):
        cm[k] = v
    if any(ids):
        ci[k] = ids
if not cm_ok:
    cm, ci = prev.get("c", {}), prev.get("ci", {})

hist = load("storico.json", {"snaps": []})
snaps = [s for s in hist.get("snaps", []) if s.get("d") != today]
snaps.append({"d": today, "t": stamp, "p": latest, "c": cm})
snaps = snaps[-45:]

json.dump({"updated": stamp, "langs": LANGS, "cmDate": cm_date, "p": latest, "c": cm, "ci": ci},
          open("prezzi_latest.json", "w"), ensure_ascii=False, separators=(",", ":"))
json.dump({"langs": LANGS, "snaps": snaps}, open("storico.json", "w"), ensure_ascii=False, separators=(",", ":"))
print("CardTrader:", len(latest), "carte - Cardmarket:", len(cm), "carte (listino del", cm_date, ") -", stamp,
      "- giorni in storico:", len(snaps))

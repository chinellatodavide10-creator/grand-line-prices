import os, json, urllib.request, urllib.error, time, datetime, re

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
                time.sleep(5)
                continue
            print("ERRORE", e.code, path, e.read()[:300])
            raise SystemExit(1)


def slug(t):
    return re.sub(r"[^a-z0-9]+", "-", (t or "").lower()).strip("-")


now = datetime.datetime.now(datetime.timezone.utc)
stamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")
today = now.strftime("%Y-%m-%d")

cards = []
for code, eid in EXPS.items():
    bps = get("/blueprints/export?expansion_id=%d" % eid)
    prods = get("/marketplace/products?expansion_id=%d" % eid)
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
        cards.append((cn, b.get("version"), [round(best[l] / 100, 2) if l in best else None for l in LANGS]))

cnt = {}
for cn, _, _ in cards:
    cnt[cn] = cnt.get(cn, 0) + 1
latest = {}
for cn, ver, arr in cards:
    if any(v is not None for v in arr):
        k = cn if cnt[cn] == 1 else cn + "~" + slug(ver)
        latest[k] = arr

try:
    hist = json.load(open("storico.json"))
except Exception:
    hist = {"snaps": []}
snaps = [s for s in hist.get("snaps", []) if s.get("d") != today]
snaps.append({"d": today, "t": stamp, "p": latest})
snaps = snaps[-60:]

json.dump({"updated": stamp, "langs": LANGS, "p": latest}, open("prezzi_latest.json", "w"), ensure_ascii=False, separators=(",", ":"))
json.dump({"langs": LANGS, "snaps": snaps}, open("storico.json", "w"), ensure_ascii=False, separators=(",", ":"))
print("Prezzi salvati:", len(latest), "carte con prezzo -", stamp, "- giorni in storico:", len(snaps))

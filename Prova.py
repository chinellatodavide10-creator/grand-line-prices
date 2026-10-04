import os, json, urllib.request, urllib.error
T = os.environ["CARDTRADER_TOKEN"]
B = "https://api.cardtrader.com/api/v2"
def get(path):
    r = urllib.request.Request(B + path, headers={"Authorization": "Bearer " + T})
    try:
        with urllib.request.urlopen(r, timeout=120) as x:
            return json.load(x)
    except urllib.error.HTTPError as e:
        print("ERRORE", e.code, path, e.read()[:300]); raise SystemExit(1)

EXP = 3332
bps = get("/blueprints/export?expansion_id=%d" % EXP)
print("Blueprint OP01:", len(bps))
print("ESEMPIO", json.dumps(bps[0], ensure_ascii=False)[:700])
n = 0
for b in bps:
    cn = str((b.get("fixed_properties") or {}).get("collector_number") or "")
    if "120" in cn or "Shanks" in (b.get("name") or ""):
        print("BP", json.dumps(b, ensure_ascii=False)[:500]); n += 1
        if n >= 8: break
prods = get("/marketplace/products?expansion_id=%d" % EXP)
print("Tipo risposta:", type(prods).__name__, "con", len(prods), "elementi")
shown = 0
for i in (prods if isinstance(prods, dict) else {}):
    lst = prods[i]
    if lst and shown < 2:
        print("PROD", i, len(lst), json.dumps(lst[0], ensure_ascii=False)[:600]); shown += 1

import os, json, urllib.request, urllib.error
T = os.environ["CARDTRADER_TOKEN"]
B = "https://api.cardtrader.com/api/v2"
try:
    r = urllib.request.Request(B + "/expansions", headers={"Authorization": "Bearer " + T})
    with urllib.request.urlopen(r, timeout=60) as x:
        ex = json.load(x)
except urllib.error.HTTPError as e:
    print("ERRORE", e.code, e.read()[:300]); raise SystemExit(1)
op = [e for e in ex if e.get("game_id") == 15]
print("Espansioni One Piece:", len(op))
for e in op:
    n = (e.get("name") or "").lower()
    if (e.get("code") or "").lower() in ("op01", "op17") or "romance dawn" in n or "strongest warriors" in n:
        print("TROVATA:", e.get("id"), e.get("code"), e.get("name"))

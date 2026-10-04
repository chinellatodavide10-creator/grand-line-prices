import json, urllib.request, urllib.error
from collections import Counter

BASE = "https://downloads.s3.cardmarket.com/productCatalog/"
UA = {"User-Agent": "Mozilla/5.0"}


def fetch(path, rng=None):
    h = dict(UA)
    if rng:
        h["Range"] = "bytes=%d-%d" % rng
    r = urllib.request.Request(BASE + path, headers=h)
    with urllib.request.urlopen(r, timeout=180) as x:
        return x.read()


game = None
for n in range(1, 41):
    try:
        t = fetch("productList/products_singles_%d.json" % n, (0, 3000)).decode("utf-8", "ignore")
    except Exception as e:
        print(n, "-", str(e)[:70])
        continue
    i = t.find("categoryName")
    print(n, t[i:i + 50].replace("\n", " "))
    if "One Piece" in t and game is None:
        game = n
print("GIOCO ONE PIECE:", game)
if game is None:
    raise SystemExit(0)

prods = json.loads(fetch("productList/products_singles_%d.json" % game))
guide = json.loads(fetch("priceGuide/price_guide_%d.json" % game))
print("Chiavi catalogo:", list(prods.keys()), "- chiavi prezzi:", list(guide.keys()))
P = {p["idProduct"]: p for p in prods.get("products", [])}
G = {g["idProduct"]: g for g in guide.get("priceGuides", [])}
print("Prodotti:", len(P), "- con prezzo:", len(G), "- data prezzi:", guide.get("createdAt"))
for i in (690368, 768234, 690369, 768236, 903879, 904803, 903880, 904804):
    print("ID", i, "PROD", json.dumps(P.get(i), ensure_ascii=False)[:300])
    print("   PREZZO", json.dumps(G.get(i), ensure_ascii=False)[:300])
print("Espansioni (id: prodotti):", Counter(p.get("idExpansion") for p in P.values()).most_common(12))

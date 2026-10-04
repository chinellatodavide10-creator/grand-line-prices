import os, io, json, urllib.request, urllib.error, time, datetime, re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

try:
    from PIL import Image
except Exception:
    Image = None

T = os.environ["CARDTRADER_TOKEN"]
MAX_IMG = int(os.environ.get("MAX_IMG") or 300)
B = "https://api.cardtrader.com/api/v2"
CT_SITE = "https://www.cardtrader.com"
CM_BASE = "https://downloads.s3.cardmarket.com/productCatalog/"
CM_GAME = 18  # One Piece su Cardmarket
GAME = 15  # One Piece su CardTrader
LANGS = ["en", "jp", "zh-CN"]
OK_COND = {"Mint", "Near Mint"}
SKIP_EXP = set()  # codici di espansione da ignorare, per esempio {"OP01"}

NEG = re.compile(r"\b(ungraded|not\s+graded|non\s+graded|raw|not\s+psa|not\s+bgs|no\s+psa|no\s+bgs|candidate|candidato|ready|for\s+(psa|bgs)|to\s+(psa|bgs)|grading|gradable)\b", re.I)
GR = re.compile(r"\b(psa|bgs|beckett)\s*[-:#]?\s*(10|9[.,]5)\b", re.I)


def grade_of(desc):
    d = desc or ""
    if NEG.search(d):
        return None
    m = GR.search(d)
    if not m:
        return None
    co = "psa" if m.group(1).lower() == "psa" else "bgs"
    g = m.group(2).replace(",", ".")
    if co == "psa" and g == "10":
        return "p10"
    if co == "bgs" and g == "10":
        return "b10"
    if co == "bgs" and g == "9.5":
        return "b95"
    return None


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
            raise
        except Exception:
            if i < 2:
                time.sleep(2)
                continue
            raise


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


def dump(path, obj):
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    json.dump(obj, open(path, "w"), ensure_ascii=False, separators=(",", ":"))


def img_url(b):
    im = b.get("image") or {}
    for u in ((im.get("show") or {}).get("url"), im.get("url"), b.get("image_url")):
        if u:
            return u if u.startswith("http") else CT_SITE + u
    return None


def download(item):
    bp, url = item
    path = "img/%s.jpg" % bp
    try:
        r = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(r, timeout=60) as x:
            data = x.read()
        if Image is not None:
            im = Image.open(io.BytesIO(data)).convert("RGB")
            if im.width > 360:
                im = im.resize((360, int(im.height * 360 / im.width)))
            buf = io.BytesIO()
            im.save(buf, "JPEG", quality=82, optimize=True)
            data = buf.getvalue()
        os.makedirs("img", exist_ok=True)
        open(path, "wb").write(data)
        return bp, True
    except Exception as e:
        print("Immagine non scaricata", bp, str(e)[:80])
        return bp, False


now = datetime.datetime.now(datetime.timezone.utc)
stamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")
today = now.strftime("%Y-%m-%d")

prev_latest = load("prezzi_latest.json", {})
prev_cat = load("catalogo.json", {})
prev_langs = {str(c[0]): c[7] for c in prev_cat.get("cards", [])} if prev_cat else {}

# --- cambio di giorno: l'ultimo rilevamento di ieri diventa il termine di confronto ---
if prev_latest.get("fmt") == 2 and prev_latest.get("updated", "")[:10] < today:
    dump("prezzi_prev.json", {"d": prev_latest["updated"][:10], "t": prev_latest["updated"], "p": prev_latest.get("p", {}),
                              "c": prev_latest.get("c", {}), "g": prev_latest.get("g", {})})
    by = {}
    for sect in ("p", "c"):
        for k, v in (prev_latest.get(sect) or {}).items():
            by.setdefault(k.split(":", 1)[0], {}).setdefault(sect, {})[k] = v
    for exp, d in by.items():
        sh = load("h/%s.json" % exp, {"snaps": []})
        snaps = [s for s in sh["snaps"] if s.get("d") != prev_latest["updated"][:10]]
        snaps.append({"d": prev_latest["updated"][:10], "t": prev_latest["updated"], "p": d.get("p", {}), "c": d.get("c", {})})
        dump("h/%s.json" % exp, {"snaps": snaps[-60:]})

# --- Cardmarket: listino ufficiale pubblico ---
try:
    guide = cm_get("priceGuide/price_guide_%d.json" % CM_GAME)
    plist = cm_get("productList/products_singles_%d.json" % CM_GAME)
    G = {g["idProduct"]: g for g in guide.get("priceGuides", [])}
    CMEXP = {p["idProduct"]: p.get("idExpansion") for p in plist.get("products", [])}
    cm_date, cm_ok = guide.get("createdAt"), True
except Exception as e:
    print("Cardmarket non raggiungibile, uso i dati precedenti:", str(e)[:100])
    G, CMEXP, cm_date, cm_ok = {}, {}, prev_latest.get("cmDate"), False

# --- CardTrader: tutte le espansioni One Piece ---
expansions = [e for e in get("/expansions") if e.get("game_id") == GAME]
expansions.sort(key=lambda e: (e.get("code") or ""))
print("Espansioni One Piece su CardTrader:", len(expansions))

P_, C_, CI_, GR_ = {}, {}, {}, {}
catalog, exps_out, to_download = [], [], []
for e in expansions:
    code = (e.get("code") or str(e["id"])).upper()
    if code in SKIP_EXP:
        continue
    try:
        bps = get("/blueprints/export?expansion_id=%d" % e["id"])
        prods = get("/marketplace/products?expansion_id=%d" % e["id"])
    except Exception as ex:
        print("Espansione saltata", code, str(ex)[:80])
        continue
    time.sleep(0.15)
    items = [(b["id"], (b.get("fixed_properties") or {}).get("collector_number"), b.get("version")) for b in bps]
    items = [i for i in items if i[1]]
    if not items:
        continue
    exps_out.append([code, e.get("name") or code])
    cn_count = Counter(cn for _, cn, _ in items)
    keys = {}
    for bp, cn, ver in items:
        k = "%s:%s" % (code, cn)
        if cn_count[cn] > 1:
            k += "~" + slug(ver)
        keys[bp] = k
    kc = Counter(keys.values())
    for bp in keys:
        if kc[keys[bp]] > 1:
            keys[bp] += "~%d" % bp
    pairs = Counter()
    for b in bps:
        ids = b.get("card_market_ids") or []
        if len(ids) >= 2 and ids[0] in CMEXP and ids[1] in CMEXP:
            pairs[(CMEXP[ids[0]], CMEXP[ids[1]])] += 1
    en_exp, jp_exp = pairs.most_common(1)[0][0] if pairs else (None, None)
    for b in bps:
        fp = b.get("fixed_properties") or {}
        cn = fp.get("collector_number")
        if not cn:
            continue
        k = keys[b["id"]]
        best, graded, langs_now = {}, {}, set()
        lst = prods.get(str(b["id"]), []) if isinstance(prods, dict) else []
        for p in lst:
            h = p.get("properties_hash") or {}
            lang = h.get("onepiece_language")
            c = p.get("price_cents")
            if lang in LANGS:
                langs_now.add(lang)
            if lang not in LANGS or c is None or p.get("price_currency") != "EUR":
                continue
            g = grade_of(p.get("description"))
            if g:
                slot = graded.setdefault(g, {}).setdefault(lang, [None, 0])
                slot[1] += p.get("quantity") or 1
                if slot[0] is None or c < slot[0]:
                    slot[0] = c
                continue
            if h.get("graded") or h.get("signed") or h.get("altered"):
                continue
            if h.get("condition") not in OK_COND:
                continue
            if lang not in best or c < best[lang]:
                best[lang] = c
        arr = [round(best[l] / 100, 2) if l in best else None for l in LANGS]
        ids = b.get("card_market_ids") or []
        en = jp = None
        if len(ids) >= 2:
            en, jp = ids[0], ids[1]
        elif len(ids) == 1:
            x = CMEXP.get(ids[0])
            if x is not None and x == en_exp:
                en = ids[0]
            elif x is not None and x == jp_exp:
                jp = ids[0]

        def pr(i):
            g = G.get(i) if i else None
            return ((g.get("trend") or None), (g.get("low") or None)) if g else (None, None)

        et, el = pr(en)
        jt, jl = pr(jp)
        v = [et, el, jt, jl]
        if any(x is not None for x in arr):
            P_[k] = arr
        if any(x is not None for x in v):
            C_[k] = v
        if en or jp:
            CI_[k] = [en, jp]
        if graded:
            GR_[k] = {g: [([round(sl[l][0] / 100, 2), sl[l][1]] if l in sl else None) for l in LANGS] for g, sl in graded.items()}
        langs = set(prev_langs.get(str(b["id"]), [])) | {{"en": "en", "jp": "jp", "zh-CN": "zh-CN"}[l] for l in langs_now}
        if not langs:
            langs = {"en"}
        has_img = os.path.exists("img/%d.jpg" % b["id"])
        u = img_url(b)
        if not has_img and u:
            to_download.append((b["id"], u))
        catalog.append([b["id"], k, code, cn, b.get("name"), b.get("version"), fp.get("onepiece_rarity"),
                        sorted(langs, key=LANGS.index), 1 if has_img else 0])

# --- immagini nuove (un tot a ogni giro) ---
done = set()
if to_download:
    batch = to_download[:MAX_IMG]
    print("Immagini da scaricare:", len(to_download), "- in questo giro:", len(batch))
    with ThreadPoolExecutor(6) as ex:
        for bp, ok in ex.map(download, batch):
            if ok:
                done.add(bp)
for row in catalog:
    if row[0] in done:
        row[8] = 1

if not cm_ok:
    C_, CI_ = prev_latest.get("c", {}), prev_latest.get("ci", {})

dump("catalogo.json", {"exps": exps_out, "cards": catalog})
dump("prezzi_latest.json", {"fmt": 2, "updated": stamp, "langs": LANGS, "cmDate": cm_date, "p": P_, "c": C_, "ci": CI_, "g": GR_})
print("Catalogo:", len(catalog), "carte in", len(exps_out), "espansioni - prezzi CardTrader:", len(P_),
      "- Cardmarket:", len(C_), "- gradate:", len(GR_), "-", stamp)

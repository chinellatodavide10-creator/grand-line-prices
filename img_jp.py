# Scarica le immagini ufficiali giapponesi delle carte da onepiece-cardgame.com
# e le salva in img/jp/<ID>.jpg (ID = es. OP17-001, OP17-001_p1). Riprende dove si e' fermato.
import os, re, sys, time, io, json, urllib.request
from PIL import Image

BASE = "https://www.onepiece-cardgame.com"
OUT = "img/jp"
MAX_NEW = int(os.environ.get("MAX_JP", "6000"))
PAUSE = float(os.environ.get("PAUSE_JP", "0.15"))
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept-Language": "ja,en;q=0.8"}
os.makedirs(OUT, exist_ok=True)

def get(url, binary=False, tries=5):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=45) as r:
                d = r.read()
            return d if binary else d.decode("utf-8", "replace")
        except Exception as e:
            err = e
            time.sleep(2 + 3 * i)
    raise RuntimeError(f"{url}: {err}")

home = get(BASE + "/cardlist/")
series = re.findall(r'<option value="(55\d{4})"', home)
series = list(dict.fromkeys(series))
print("serie trovate:", len(series))
if not series:
    print("Nessuna serie trovata: il sito potrebbe bloccare questo server."); sys.exit(1)

new = 0; skipped = 0; failed = []
seen = set()
for s in series:
    try:
        html = get(f"{BASE}/cardlist/?series={s}")
    except Exception as e:
        print("serie", s, "non letta:", e); failed.append(s); continue
    for m in re.finditer(r'<dl class="modalCol" id="([^"]+)">.*?data-src="([^"]+)"', html, re.S):
        cid, src = m.group(1), m.group(2)
        if cid in seen: continue
        seen.add(cid)
        path = f"{OUT}/{cid}.jpg"
        if os.path.exists(path): skipped += 1; continue
        if new >= MAX_NEW: continue
        url = BASE + "/images/cardlist/card/" + src.split("/card/")[-1].split("?")[0]
        try:
            im = Image.open(io.BytesIO(get(url, True))).convert("RGB")
            w = 320; h = round(im.height * w / im.width)
            im.resize((w, h), Image.LANCZOS).save(path, "JPEG", quality=72, optimize=True)
            new += 1
        except Exception as e:
            print("immagine non scaricata", cid, e); failed.append(cid)
        time.sleep(PAUSE)
    print("serie", s, "ok; nuove finora", new, flush=True)

ids = sorted(f[:-4] for f in os.listdir(OUT) if f.endswith(".jpg"))
json.dump(ids, open(f"{OUT}/ids.json", "w"), separators=(",", ":"))
print(f"Fatto: {new} nuove, {skipped} gia' presenti, {len(ids)} totali, {len(failed)} errori")

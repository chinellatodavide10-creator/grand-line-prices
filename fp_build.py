# Crea le "impronte" visive di tutte le carte per il riconoscimento con la fotocamera.
# Legge img/<id>.jpg (inglesi) e img/jp/<ID>.jpg (giapponesi) e scrive fp.json + fp.bin
import os, json
from PIL import Image
GW, GH = 10, 14          # griglia dell'impronta
X0, X1, Y0, Y1 = 0.08, 0.92, 0.06, 0.94   # parte centrale della carta (taglia il bordo)
def fp(path):
    im = Image.open(path).convert("RGB")
    w, h = im.size
    box = (w * X0, h * Y0, w * X1, h * Y1)
    t = im.resize((GW, GH), Image.BOX, box=box)
    return bytes(t.tobytes())
en = sorted(f[:-4] for f in os.listdir("img") if f.endswith(".jpg") and f[:-4].isdigit()) if os.path.isdir("img") else []
jp = sorted(f[:-4] for f in os.listdir("img/jp") if f.endswith(".jpg")) if os.path.isdir("img/jp") else []
data = bytearray(); ok_en = []; ok_jp = []
for i in en:
    try: data += fp(f"img/{i}.jpg"); ok_en.append(i)
    except Exception as e: print("salto", i, e)
for i in jp:
    try: data += fp(f"img/jp/{i}.jpg"); ok_jp.append(i)
    except Exception as e: print("salto", i, e)
open("fp.bin", "wb").write(bytes(data))
json.dump({"gw": GW, "gh": GH, "box": [X0, X1, Y0, Y1], "en": ok_en, "jp": ok_jp}, open("fp.json", "w"), separators=(",", ":"))
print("impronte:", len(ok_en), "inglesi,", len(ok_jp), "giapponesi,", len(data), "byte")

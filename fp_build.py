# Crea le "impronte" visive di tutte le carte per il riconoscimento con la fotocamera.
# Legge img/<id>.jpg (inglesi) e img/jp/<ID>.jpg (giapponesi) e scrive:
#   fp.json + fp.bin  (aspetto generale della carta)
#   fpt.bin           (impronta della zona di testo: serve a distinguere inglese e giapponese)
import os, json
from PIL import Image
GW, GH = 10, 14          # griglia dell'impronta
X0, X1, Y0, Y1 = 0.08, 0.92, 0.06, 0.94   # parte centrale della carta (taglia il bordo)
TW, TH = 24, 8           # griglia della zona di testo
TX0, TX1, TY0, TY1 = 0.07, 0.93, 0.64, 0.93
def fp(path):
    im = Image.open(path).convert("RGB")
    w, h = im.size
    t = im.resize((GW, GH), Image.BOX, box=(w * X0, h * Y0, w * X1, h * Y1))
    return bytes(t.tobytes())
def fpt(path):
    im = Image.open(path).convert("L")
    w, h = im.size
    g = im.resize((TW * 4, TH * 4), Image.BOX, box=(w * TX0, h * TY0, w * TX1, h * TY1))
    W, H = TW * 4, TH * 4
    px = list(g.getdata())
    mean = bytearray(TW * TH); en = bytearray(TW * TH)
    for gy in range(TH):
        for gx in range(TW):
            m = 0; e = 0
            for yy in range(4):
                for xx in range(4):
                    X = gx * 4 + xx; Y = gy * 4 + yy; v = px[Y * W + X]
                    m += v
                    e += abs(v - px[Y * W + min(W - 1, X + 1)]) + abs(v - px[min(H - 1, Y + 1) * W + X])
            mean[gy * TW + gx] = round(m / 16)
            en[gy * TW + gx] = min(255, round(e / 16 * 4))
    return bytes(mean) + bytes(en)
en = sorted(f[:-4] for f in os.listdir("img") if f.endswith(".jpg") and f[:-4].isdigit()) if os.path.isdir("img") else []
jp = sorted(f[:-4] for f in os.listdir("img/jp") if f.endswith(".jpg")) if os.path.isdir("img/jp") else []
data = bytearray(); tdata = bytearray(); ok_en = []; ok_jp = []
for i in en:
    try:
        p = f"img/{i}.jpg"; a = fp(p); b = fpt(p); data += a; tdata += b; ok_en.append(i)
    except Exception as e: print("salto", i, e)
for i in jp:
    try:
        p = f"img/jp/{i}.jpg"; a = fp(p); b = fpt(p); data += a; tdata += b; ok_jp.append(i)
    except Exception as e: print("salto", i, e)
open("fp.bin", "wb").write(bytes(data))
open("fpt.bin", "wb").write(bytes(tdata))
json.dump({"gw": GW, "gh": GH, "box": [X0, X1, Y0, Y1], "en": ok_en, "jp": ok_jp}, open("fp.json", "w"), separators=(",", ":"))
print("impronte:", len(ok_en), "inglesi,", len(ok_jp), "giapponesi,", len(data), "byte;", "testo:", len(tdata), "byte")

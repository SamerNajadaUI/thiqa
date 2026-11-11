#!/usr/bin/env python3
"""
قصّة الشعر للعبة «تسريحة لاعب»: لكل لاعب (مستوى 1-2) بصورة، بنلاقي الوجه (YuNet من OpenCV)
وبنحسب مستطيل من فوق الراس لحد فوق الحواجب، عشان اللعبة تعرض الشعر بس بدون العيون والوجه.

الناتج: docs/games/hair.json  { "c": { "<id>": [x, y, w, h, نسبة الصورة] } }  (كلها نسب من الصورة)
وصورة مراجعة: hair_sheet.jpg (بترفعها الـCI كـartifact)
"""
import io, json, sys, time, urllib.request
from pathlib import Path
import numpy as np, cv2
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs/games/hair.json"
UA = "AbuOdehGame/1.0 (https://github.com/SamerNajadaUI/thiqa)"
MODEL = "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"

def get(url, tries=3):
    for k in range(tries):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30).read()
        except Exception as e:
            if k == tries - 1: raise
            time.sleep(2 + 3 * k)

def main():
    mp = Path("/tmp/yunet.onnx")
    if not mp.exists(): mp.write_bytes(get(MODEL))
    players = json.loads((ROOT / "docs/games/players.json").read_text(encoding="utf-8"))["players"]
    want = [p for p in players if p.get("lv", 9) <= 2 and p.get("img")]
    out, thumbs, miss = {}, [], 0
    for i, p in enumerate(want):
        try:
            im = Image.open(io.BytesIO(get(p["img"]))).convert("RGB")
        except Exception as e:
            print("✗ تحميل", p["a"], e, file=sys.stderr); miss += 1; continue
        W, H = im.size
        a = cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR)
        det = cv2.FaceDetectorYN.create(str(mp), "", (W, H), 0.75, 0.3, 50)
        _, faces = det.detect(a)
        if faces is None or not len(faces):
            print("– بدون وجه", p["a"], file=sys.stderr); miss += 1; continue
        faces = sorted(faces, key=lambda f: -f[2] * f[3])
        f = faces[0]
        if len(faces) > 1 and faces[1][2] * faces[1][3] > 0.5 * f[2] * f[3]:
            print("– أكثر من وجه", p["a"], file=sys.stderr); miss += 1; continue
        fx, fy, fw, fh = f[:4]
        if fw < 0.12 * W:
            print("– الوجه صغير", p["a"], file=sys.stderr); miss += 1; continue
        eye_y = (f[5] + f[7]) / 2
        cx = fx + fw / 2
        y1 = eye_y - 0.32 * fh            # فوق الحواجب
        y0 = max(0, fy - 0.7 * fh)        # فوق الراس
        x0, x1 = max(0, cx - 0.9 * fw), min(W, cx + 0.9 * fw)
        if y1 - y0 < 0.3 * fh or y1 <= 0:
            print("– ما في شعر كفاية فوق", p["a"], file=sys.stderr); miss += 1; continue
        out[p["id"]] = [round(x0 / W, 4), round(y0 / H, 4), round((x1 - x0) / W, 4), round((y1 - y0) / H, 4), round(W / H, 4)]
        if len(thumbs) < 80:
            t = im.crop((int(x0), int(y0), int(x1), int(y1))); t.thumbnail((180, 120)); thumbs.append(t)
        if i % 50 == 0: print(f"{i}/{len(want)} ✓{len(out)}", file=sys.stderr, flush=True)
        time.sleep(0.15)
    OUT.write_text(json.dumps({"generated": time.strftime("%Y-%m-%d"), "c": out}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"hair.json: {len(out)} لاعب، {miss} انشالوا", file=sys.stderr)
    if thumbs:
        sheet = Image.new("RGB", (8 * 184, ((len(thumbs) + 7) // 8) * 124), "white")
        for k, t in enumerate(thumbs): sheet.paste(t, ((k % 8) * 184 + 2, (k // 8) * 124 + 2))
        sheet.save(ROOT / "hair_sheet.jpg", quality=80)

if __name__ == "__main__":
    main()

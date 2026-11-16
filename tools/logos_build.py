#!/usr/bin/env python3
"""يبني شعارات «جمع نقاط» من حزمة Simple Icons (CC0) المحمّلة محلياً.
الاستعمال: python3 tools/logos_build.py /path/to/simple-icons/package
بيقرأ engine/data/logos.txt ويكتب docs/games/pq/logos/<slug>.svg (لون الماركة على مربع أبيض، أو على ليل إذا اللون فاتح)."""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PKG = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/dl/si/package")
OUT = ROOT / "docs" / "games" / "pq" / "logos"
OUT.mkdir(parents=True, exist_ok=True)
data = json.loads((PKG / "data" / "simple-icons.json").read_text())
data = data if isinstance(data, list) else data["icons"]
hexes = {}
for d in data:
    s = d.get("slug") or re.sub(r"[^a-z0-9]", "", d["title"].lower())
    hexes[s] = d["hex"]


def lum(h):
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def build(slug):
    src = PKG / "icons" / f"{slug}.svg"
    if not src.exists():
        return False
    path = re.search(r'<path d="([^"]+)"', src.read_text()).group(1)
    h = hexes.get(slug, "111111")
    bg = "#fff"
    if lum(h) > 0.55:          # لون فاتح (أصفر، أبيض...) ما بيبين على أبيض
        bg = "#16113A"
    if lum(h) > 0.93 and bg == "#fff":
        h = "111111"
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-6 -6 36 36"><rect x="-6" y="-6" width="36" height="36" rx="7" fill="{bg}"/>'
           f'<path fill="#{h}" d="{path}"/></svg>')
    (OUT / f"{slug}.svg").write_text(svg)
    return True


if __name__ == "__main__":
    slugs = [l.split("|")[0] for l in (ROOT / "engine" / "data" / "logos.txt").read_text(encoding="utf-8").splitlines() if l and not l.startswith("#")]
    extra = sys.argv[2:]
    ok = [s for s in slugs + extra if build(s)]
    print(len(ok), "شعار")

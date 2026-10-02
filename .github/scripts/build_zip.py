#!/usr/bin/env python3
"""Build the addon zip, sync addon.xml <news> with changelog.txt, prune old zips."""
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ADDON_DIR = ROOT / "plugin.video.corridor"
ADDON_ID = ADDON_DIR.name
EXCLUDE = {"changelog.txt.bak"}


def vkey(v):
    return tuple(int(p) for p in re.findall(r"\d+", v))


def main():
    xml_path = ADDON_DIR / "addon.xml"
    xml = xml_path.read_text(encoding="utf-8")
    version = re.search(r'<addon[^>]*\sversion="([^"]+)"', xml).group(1)

    # Current version's changelog section only
    log = (ADDON_DIR / "changelog.txt").read_text(encoding="utf-8")
    sections = re.split(r"(?m)^(?=v\d)", log)
    current = next((s for s in sections if s.startswith(f"v{version}\n") or s.startswith(f"v{version} ")), None)
    if current is None:
        sys.exit(f"changelog.txt has no section for v{version}")
    news = current.strip()
    esc = news.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    xml = re.sub(r"<news>.*?</news>", lambda m: f"<news>{esc}</news>", xml, flags=re.S)
    xml_path.write_text(xml, encoding="utf-8")

    zip_path = ROOT / f"{ADDON_ID}-{version}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(ADDON_DIR.rglob("*")):
            if f.is_file() and "__pycache__" not in f.parts and f.suffix != ".pyc" and f.name not in EXCLUDE:
                z.write(f, f"{ADDON_ID}/{f.relative_to(ADDON_DIR).as_posix()}")

    # Keep current + previous version only
    zips = {}
    for p in ROOT.glob(f"{ADDON_ID}-*.zip"):
        m = re.fullmatch(re.escape(ADDON_ID) + r"-(\d+(?:\.\d+)*)\.zip", p.name)
        if m:
            zips[m.group(1)] = p
    keep = sorted(zips, key=vkey)[-2:]
    for v, p in zips.items():
        if v not in keep:
            p.unlink()
            print("removed", p.name)
    print("built", zip_path.name)


main()

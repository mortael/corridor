#!/usr/bin/env python3
"""Build the addon zip, sync addon.xml <news> with changelog.txt, prune old zips."""
import difflib
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


SKIP = {"changelog.txt"}


def previous_zip(version):
    best = None
    for p in ROOT.glob(f"{ADDON_ID}-*.zip"):
        m = re.fullmatch(re.escape(ADDON_ID) + r"-(\d+(?:\.\d+)*)\.zip", p.name)
        if m and vkey(m.group(1)) < vkey(version) and (best is None or vkey(m.group(1)) > vkey(best[0])):
            best = (m.group(1), p)
    return best


def read_prev(zpath):
    out = {}
    prefix = ADDON_ID + "/"
    with zipfile.ZipFile(zpath) as z:
        for n in z.namelist():
            rel = n[len(prefix):] if n.startswith(prefix) else n
            if rel and not n.endswith("/") and rel not in SKIP:
                out[rel] = z.read(n)
    return out


def read_current():
    out = {}
    for f in ADDON_DIR.rglob("*"):
        if f.is_file() and "__pycache__" not in f.parts and f.suffix != ".pyc" and f.name not in EXCLUDE:
            rel = f.relative_to(ADDON_DIR).as_posix()
            if rel not in SKIP:
                out[rel] = f.read_bytes()
    return out


def line_delta(old, new):
    try:
        a = old.decode("utf-8").splitlines()
        b = new.decode("utf-8").splitlines()
    except UnicodeDecodeError:
        return None
    add = rem = 0
    for line in difflib.ndiff(a, b):
        if line.startswith("+ "):
            add += 1
        elif line.startswith("- "):
            rem += 1
    return add, rem


def generate_section(version):
    prev = previous_zip(version)
    if prev is None:
        return f"v{version}\n- Release {version}\n"
    pv, pzip = prev
    old, new = read_prev(pzip), read_current()
    lines = []
    for f in sorted(new.keys() - old.keys()):
        lines.append(f"- Added {f}")
    for f in sorted(old.keys() - new.keys()):
        lines.append(f"- Removed {f}")
    for f in sorted(new.keys() & old.keys()):
        if new[f] != old[f]:
            d = line_delta(old[f], new[f])
            lines.append(f"- Updated {f}" + (f" (+{d[0]}/-{d[1]} lines)" if d else ""))
    if not lines:
        lines = ["- No code changes"]
    return f"v{version} (changes since v{pv})\n" + "\n".join(lines) + "\n"


def normalize(rel, data):
    if rel == "addon.xml":
        t = data.decode("utf-8")
        t = re.sub(r'(<addon[^>]*\sversion=")[^"]*"', r'\1"', t, count=1)
        t = re.sub(r"<news>.*?</news>", "<news/>", t, flags=re.S)
        return t.encode("utf-8")
    return data


def maybe_bump(xml, version):
    """If a zip for this version exists and the code changed since, bump the patch version."""
    zpath = ROOT / f"{ADDON_ID}-{version}.zip"
    if not zpath.exists():
        return xml, version
    old, new = read_prev(zpath), read_current()
    old["addon.xml"] = old.get("addon.xml", b"")
    keys = old.keys() | new.keys()
    if all(normalize(k, old.get(k, b"")) == normalize(k, new.get(k, b"")) for k in keys) and old.keys() == new.keys():
        return xml, version
    parts = [int(x) for x in version.split(".")]
    parts[-1] += 1
    nv = ".".join(map(str, parts))
    xml = re.sub(r'(<addon[^>]*\sversion=")[^"]*"', lambda m: f'{m.group(1)}{nv}"', xml, count=1)
    (ADDON_DIR / "addon.xml").write_text(xml, encoding="utf-8")
    print(f"bumped version {version} -> {nv}")
    return xml, nv


def main():
    xml_path = ADDON_DIR / "addon.xml"
    xml = xml_path.read_text(encoding="utf-8")
    version = re.search(r'<addon[^>]*\sversion="([^"]+)"', xml).group(1)
    xml, version = maybe_bump(xml, version)

    # Current version's changelog section only
    log_path = ADDON_DIR / "changelog.txt"
    log = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
    sections = re.split(r"(?m)^(?=v\d)", log)
    current = next((s for s in sections if re.match(rf"v{re.escape(version)}(\s|$)", s)), None)
    if current is None:
        current = generate_section(version)
        log_path.write_text(current + "\n" + log, encoding="utf-8")
        print(f"generated changelog section for v{version}")
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

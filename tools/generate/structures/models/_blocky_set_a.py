"""Shared helpers for the blocky_<family>_convert.py one-shot scripts (crusher, armoury, concrete_mixer, crop_farm)."""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import bblib  # noqa: E402

PACK = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))


def els(m, name, group="frame"):
    """All elements whose name starts with `name` (exact match first, prefix otherwise)."""
    allc = m.elements_in(group)
    ex = [e for e in allc if e["name"] == name]
    return ex or [e for e in allc if e["name"].startswith(name)]


def box(e, frm, to):
    """Set an unrotated element's box (and origin = centre)."""
    e["from"] = [float(v) for v in frm]
    e["to"] = [float(v) for v in to]
    if not any(e.get("rotation", [0, 0, 0])):
        e["origin"] = [(a + b) / 2 for a, b in zip(frm, to)]
    return e


def run(family, convert):
    ap = argparse.ArgumentParser()
    ap.add_argument("--src")
    ap.add_argument("--out", default=os.path.join(PACK, "bbmodels", "structure_%s.bbmodel" % family))
    a = ap.parse_args()
    if a.src:
        m = bblib.Model.load(a.src)
    else:
        raw = subprocess.check_output(["git", "-C", PACK, "show", "HEAD:bbmodels/structure_%s.bbmodel" % family])
        m = bblib.Model(json.loads(raw))
    convert(m)
    m.save(a.out)
    print("wrote", a.out)

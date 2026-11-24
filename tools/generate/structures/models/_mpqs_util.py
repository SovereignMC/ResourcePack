"""Small helpers shared by the blocky_<family>_convert.py scripts of munitions_factory, power_plant, quarry, sawmill."""
import os
import sys
import json
import subprocess
import uuid as _uuid

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import bblib  # noqa: E402

PACK = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))


def load_head(family):
    raw = subprocess.check_output(["git", "-C", PACK, "show", "HEAD:bbmodels/structure_%s.bbmodel" % family])
    return bblib.Model(json.loads(raw))


def els(m, group, pred=None):
    """Elements (recursive) of `group` for which pred(e) is true."""
    return [e for e in m.elements_in(group) if pred is None or pred(e)]


def cx(e, axis=0):
    return (e["from"][axis] + e["to"][axis]) / 2


def setbox(m, e, frm, to):
    e["from"] = [bblib._num(v) for v in frm]
    e["to"] = [bblib._num(v) for v in to]
    if not any(e.get("rotation", [0, 0, 0])):
        e["origin"] = [bblib._num((a + b) / 2) for a, b in zip(frm, to)]


def make_group(m, name, parent, origin, items):
    """New group `name` under `parent` (name) holding the top-level `items` (dicts)."""
    p = m.group(parent)
    u = str(_uuid.uuid5(bblib.UUID_NS, "mpqs|%s" % name))
    g = {"name": name, "uuid": u, "export": True, "locked": False, "scope": 0, "selected": False,
         "visibility": True, "_static": {"properties": {}, "temp_data": {}},
         "origin": [bblib._num(v) for v in origin], "rotation": [0, 0, 0], "color": 0, "children": [],
         "reset": False, "shade": True, "mirror_uv": False, "autouv": 0, "isOpen": False, "primary_selected": False}
    m.d["groups"].append(g)
    node = {"uuid": u, "isOpen": False, "children": []}
    m.node[p["uuid"]]["children"].append(node)
    for it in items:
        old = m.parent.get(it["uuid"])
        lst = m.children_list(old)
        for c in list(lst):
            if (c if isinstance(c, str) else c["uuid"]) == it["uuid"]:
                lst.remove(c)
                node["children"].append(c)
    m.reindex()
    return g


def scale_anim(m, group, channel, axis, factor):
    g = m.group(group)
    for a in m.d["animations"]:
        an = a["animators"].get(g["uuid"])
        for k in (an or {}).get("keyframes", []):
            if k["channel"] == channel:
                for dp in k["data_points"]:
                    dp[axis] = str(bblib._num(float(dp[axis]) * factor))


def write_override(name, **kw):
    p = os.path.join(os.path.dirname(HERE), "state_overrides", name + ".json")
    with open(p, "w") as f:
        json.dump(kw, f, indent=2)
        f.write("\n")


def setx(e, x0, x1):
    """Change only the X extent of an element (rotated cubes keep their rotation; origin x re-centred)."""
    e["from"][0], e["to"][0] = bblib._num(x0), bblib._num(x1)
    e["origin"][0] = bblib._num((x0 + x1) / 2)


def bbox(m, sel):
    items = m._sel(sel)
    es, _ = m._all_in(items)
    lo = [min(e["from"][i] for e in es) for i in range(3)]
    hi = [max(e["to"][i] for e in es) for i in range(3)]
    return lo, hi


def place(m, sel, factor, tx, tz, y_floor=2.0):
    """Scale a selection about its footprint centre / floor level, then move the footprint centre to (tx, tz)."""
    lo, hi = bbox(m, sel)
    c = ((lo[0] + hi[0]) / 2, (lo[2] + hi[2]) / 2)
    m.scale(sel, factor, about=(c[0], y_floor, c[1]))
    m.translate(sel, dx=tx - c[0], dz=tz - c[1])

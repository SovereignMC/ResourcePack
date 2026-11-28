"""PlaneChase head canvas generator, Phase 1 (palette format 4).

Reads every block state from the vanilla data report (blocks.json) and every blockstate, model and
texture from a client jar, resolves each state the way a block display renders it (variant pick with
RandomSource 42, multipart parts reseeded per part, variant x/y rotation and uvlock baked into the
elements, default tints), deduplicates the rendered shapes, and writes:

  * the resource pack pieces: the palette sprite (planechase:block/canvas_palette), the 2x2x2 cell
    group models (planechase:canvas/g_<gx>_<gy>_<gz>), one item definition per tile size
    (planechase:canvas_<x>x<y>x<z>, a composite of condition-gated groups), the item-entity translucent
    shaders (vanilla + sgvm gun viewmodel + canvas) and the shared decoder include;
  * canvas-shapes.json for PlaneChase (normalised blockstate -> shape id and flags).

Signs are built from PlaneChase's SignBoardMapper pieces (planks board, stripped-log post or
beam, chains), as PlaneChase draws them with block displays. States with no model elements (chests, beds, banners, skulls, shulker boxes: block entity
renderers) or more than MAX_ELEMENTS elements get no shape, so PlaneChase keeps an entity display
for them. Animated textures use their first frame.

Usage:
  python -I canvas_gen.py <client.jar> <blocks.json> <pack_out.zip> <canvas-shapes.json> [--iris <dir>]
"""

import io
import json
import math
import sys
import zipfile
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
NS = "planechase"
MARKER = (80, 67, 86, 255)
SPRITE_W = 256
SHAPE_ROW = 16
ELEMENT_TEXELS = 30
SHAPE_TEXELS = 4
MAX_ELEMENTS = 32
FORMAT = 4
FACES = ["down", "up", "north", "south", "west", "east"]
DIRECTIONS = [(0, -1, 0), (0, 1, 0), (0, 0, -1), (0, 0, 1), (-1, 0, 0), (1, 0, 0)]
FACE_INFO = [
    (0, 0, 1), (0, 0, 0), (1, 0, 0), (1, 0, 1),
    (0, 1, 0), (0, 1, 1), (1, 1, 1), (1, 1, 0),
    (1, 1, 0), (1, 0, 0), (0, 0, 0), (0, 1, 0),
    (0, 1, 1), (0, 0, 1), (1, 0, 1), (1, 1, 1),
    (0, 1, 0), (0, 0, 0), (0, 0, 1), (0, 1, 1),
    (1, 1, 1), (1, 0, 1), (1, 0, 0), (1, 1, 0),
]
TILE_LADDER = [(16, 8, 16), (24, 8, 24), (32, 12, 32), (48, 12, 48), (48, 24, 48)]
MAX_TILE = TILE_LADDER[-1]

RENAMED = {"chain": "iron_chain"}
TRANSLUCENT_SUFFIXES = ("stained_glass", "stained_glass_pane")
TRANSLUCENT_BLOCKS = {"ice", "frosted_ice", "slime_block", "honey_block", "tinted_glass", "nether_portal"}


class JavaRandom:
    MASK = (1 << 48) - 1

    def __init__(self, seed):
        self.set_seed(seed)

    def set_seed(self, seed):
        self.seed = (seed ^ 0x5DEECE66D) & self.MASK

    def next(self, bits):
        self.seed = (self.seed * 0x5DEECE66D + 0xB) & self.MASK
        value = self.seed >> (48 - bits)
        if value >= 1 << (bits - 1):
            value -= 1 << bits
        return value

    def next_int(self, bound):
        if bound & -bound == bound:
            return (bound * self.next(31)) >> 31
        while True:
            bits = self.next(31)
            value = bits % bound
            if bits - value + (bound - 1) < (1 << 31):
                return value

    def next_long(self):
        value = (self.next(32) << 32) + self.next(32)
        value &= (1 << 64) - 1
        return value - (1 << 64) if value >= 1 << 63 else value


def mat_mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def mat_vec(m, v):
    return [sum(m[i][k] * v[k] for k in range(3)) for i in range(3)]


def quarter(deg):
    deg %= 360
    return {0: (1, 0), 90: (0, 1), 180: (-1, 0), 270: (0, -1)}[deg]


def rot_x(deg):
    c, s = quarter(deg)
    return [[1, 0, 0], [0, c, -s], [0, s, c]]


def rot_y(deg):
    c, s = quarter(deg)
    return [[c, 0, s], [0, 1, 0], [-s, 0, c]]


def variant_matrix(x, y):
    return mat_mul(rot_y(-y), rot_x(-x))


def element_matrix(axis, angle):
    a = math.radians(angle)
    c, s = math.cos(a), math.sin(a)
    if axis == 0:
        return [[1, 0, 0], [0, c, -s], [0, s, c]]
    if axis == 1:
        return [[c, 0, s], [0, 1, 0], [-s, 0, c]]
    return [[c, -s, 0], [s, c, 0], [0, 0, 1]]


def around_center(m, p):
    q = mat_vec(m, [p[0] - 8, p[1] - 8, p[2] - 8])
    return [round(q[0] + 8, 6), round(q[1] + 8, 6), round(q[2] + 8, 6)]


def direction_index(v):
    best, best_dot = 0, -2.0
    for index, d in enumerate(DIRECTIONS):
        dot = v[0] * d[0] + v[1] * d[1] + v[2] * d[2]
        if dot > best_dot + 1e-9:
            best, best_dot = index, dot
    return best


def default_uv(f, t, face):
    return [
        [f[0], 16 - t[2], t[0], 16 - f[2]],
        [f[0], f[2], t[0], t[2]],
        [16 - t[0], 16 - t[1], 16 - f[0], 16 - f[1]],
        [f[0], 16 - t[1], t[0], 16 - f[1]],
        [f[2], 16 - t[1], t[2], 16 - f[1]],
        [16 - t[2], 16 - t[1], 16 - f[2], 16 - f[1]],
    ][face]


def vertex_uv(uv, rotation, vertex):
    i = (vertex + rotation // 90) % 4
    u = uv[0] if i in (0, 1) else uv[2]
    v = uv[1] if i in (0, 3) else uv[3]
    return u, v


def face_corner(face, vertex, lo, hi):
    e = FACE_INFO[face * 4 + vertex]
    return [hi[k] if e[k] else lo[k] for k in range(3)]


def coord16(value):
    encoded = round((value + 16) * 256)
    if not 0 <= encoded < 65536:
        raise ValueError(f"coordinate {value} outside the palette range")
    return encoded >> 8, encoded & 255


def uv8(value):
    return max(0, min(255, round(value * 16)))


def box_byte(value, up):
    scaled = (value + 16) * 4
    return max(0, min(255, math.ceil(scaled - 1e-6) if up else math.floor(scaled + 1e-6)))


class Client:
    def __init__(self, jar):
        self.zip = zipfile.ZipFile(jar)
        self.names = set(self.zip.namelist())
        self.models = {}
        self.textures = {}

    def json(self, path):
        return json.loads(self.zip.read(path))

    @staticmethod
    def split(name):
        ns, _, path = name.partition(":") if ":" in name else ("minecraft", "", name)
        return ns, path

    def model(self, name):
        if name in self.models:
            return self.models[name]
        ns, path = self.split(name)
        data = self.json(f"assets/{ns}/models/{path}.json")
        textures = dict(data.get("textures", {}))
        elements = data.get("elements")
        if "parent" in data and not data["parent"].startswith("builtin/"):
            parent_textures, parent_elements = self.model(data["parent"])
            merged = dict(parent_textures)
            merged.update(textures)
            textures = merged
            elements = elements if elements is not None else parent_elements
        result = (textures, elements or [])
        self.models[name] = result
        return result

    def texture(self, name):
        if name in self.textures:
            return self.textures[name]
        ns, path = self.split(name)
        file = f"assets/{ns}/textures/{path}.png"
        if file not in self.names:
            self.textures[name] = None
            return None
        image = Image.open(io.BytesIO(self.zip.read(file))).convert("RGBA")
        w, h = image.size
        image = image.crop((0, 0, w, min(w, h)))
        if image.size != (16, 16):
            image = image.resize((16, 16), Image.NEAREST)
        pixels = [image.getpixel((x, y)) for y in range(16) for x in range(16)]
        self.textures[name] = pixels
        return pixels

    def colormap(self, name, x, y):
        image = Image.open(io.BytesIO(self.zip.read(f"assets/minecraft/textures/colormap/{name}.png"))).convert("RGB")
        return image.getpixel((x, y))


def matches(when, props):
    if "OR" in when:
        return any(matches(w, props) for w in when["OR"])
    if "AND" in when:
        return all(matches(w, props) for w in when["AND"])
    for key, value in when.items():
        if str(props.get(key)) not in str(value).split("|"):
            return False
    return True


def pick(entry, random):
    if isinstance(entry, dict):
        return entry
    total = sum(v.get("weight", 1) for v in entry)
    roll = random.next_int(total)
    for v in entry:
        roll -= v.get("weight", 1)
        if roll < 0:
            return v
    return entry[-1]


def parts_of(client, block, props):
    file = f"assets/minecraft/blockstates/{block}.json"
    if file not in client.names:
        return []
    data = client.json(file)
    random = JavaRandom(42)
    if "variants" in data:
        for key, entry in data["variants"].items():
            wanted = dict(p.split("=") for p in key.split(",") if p)
            if all(str(props.get(k)) == v for k, v in wanted.items()):
                return [pick(entry, random)]
        return []
    seed = random.next_long()
    parts = []
    for part in data.get("multipart", []):
        if "when" in part and not matches(part["when"], props):
            continue
        random.set_seed(seed)
        parts.append(pick(part["apply"], random))
    return parts


class Tints:
    def __init__(self, client):
        grass = client.colormap("grass", 127, 127)
        self.grass = grass
        self.foliage = (0x48, 0xB5, 0x18)
        self.table = {
            "birch_leaves": (0x80, 0xA7, 0x55),
            "spruce_leaves": (0x61, 0x99, 0x61),
            "mangrove_leaves": (0x92, 0xC6, 0x48),
            "lily_pad": (0x20, 0x80, 0x30),
            "water_cauldron": (0x3F, 0x76, 0xE4),
            "attached_melon_stem": (0xE0, 0xC7, 0x1C),
            "attached_pumpkin_stem": (0xE0, 0xC7, 0x1C),
        }

    def of(self, block, props):
        if block in self.table:
            return self.table[block]
        if block == "redstone_wire":
            power = int(props.get("power", 0)) / 15.0
            r = power * 0.6 + (0.4 if power > 0 else 0.3)
            g = max(0.0, power * power * 0.7 - 0.5)
            b = max(0.0, power * power * 0.6 - 0.7)
            return tuple(int(max(0, min(1, c)) * 255) for c in (r, g, b))
        if block in ("melon_stem", "pumpkin_stem"):
            age = int(props.get("age", 0))
            return (age * 32, 255 - age * 8, age * 4)
        if block.endswith("leaves") or block in ("vine", "pale_hanging_moss"):
            return self.foliage if block != "pale_oak_leaves" and block != "azalea_leaves" and block != "flowering_azalea_leaves" and block != "cherry_leaves" else (255, 255, 255)
        if block in ("grass_block", "short_grass", "tall_grass", "fern", "large_fern", "potted_fern",
                     "sugar_cane", "bush"):
            return self.grass
        return (255, 255, 255)


def bake_state(client, tints, block, props, warnings):
    parts = parts_of(client, block, props)
    elements = []
    tint = tints.of(block, props)
    translucent = block in TRANSLUCENT_BLOCKS or block.endswith(TRANSLUCENT_SUFFIXES)
    for part in parts:
        textures, model_elements = client.model(part["model"])
        m = variant_matrix(part.get("x", 0), part.get("y", 0))
        uvlock = part.get("uvlock", False) and (part.get("x", 0) or part.get("y", 0))
        for element in model_elements:
            lo0, hi0 = element["from"], element["to"]
            corners = [around_center(m, [hi0[0] if i & 1 else lo0[0], hi0[1] if i & 2 else lo0[1],
                                         hi0[2] if i & 4 else lo0[2]]) for i in range(8)]
            lo = [min(c[k] for c in corners) for k in range(3)]
            hi = [max(c[k] for c in corners) for k in range(3)]
            rotation = element.get("rotation")
            spin = (0, 128, 0)
            pivot = [8, 8, 8]
            elem_r = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
            if rotation and rotation.get("angle", 0):
                axis = "xyz".index(rotation["axis"])
                unit = [0, 0, 0]
                unit[axis] = 1
                turned = mat_vec(m, unit)
                new_axis = max(range(3), key=lambda k: abs(turned[k]))
                angle = rotation["angle"] * (1 if turned[new_axis] > 0 else -1)
                spin = (new_axis + 1, round(angle * 2) + 128, 1 if rotation.get("rescale") else 0)
                pivot = around_center(m, rotation.get("origin", [8, 8, 8]))
                elem_r = element_matrix(new_axis, angle)
            faces = [None] * 6
            for face_index, name in enumerate(FACES):
                spec = element.get("faces", {}).get(name)
                if spec is None:
                    continue
                ref = spec.get("texture", "")
                seen = 0
                while ref.startswith("#") and seen < 16:
                    ref = textures.get(ref[1:], "")
                    seen += 1
                if not ref or ref.startswith("#") or client.texture(ref) is None:
                    warnings.add(f"{block}: missing texture {spec.get('texture')}")
                    continue
                new_face = direction_index(mat_vec(m, DIRECTIONS[face_index]))
                light = direction_index(mat_vec(elem_r, DIRECTIONS[new_face]))
                if uvlock:
                    uv = default_uv(lo, hi, new_face)
                    corner_uv = {j: vertex_uv(uv, 0, j) for j in range(4)}
                else:
                    uv = spec.get("uv") or default_uv(lo0, hi0, face_index)
                    rot = spec.get("rotation", 0)
                    corner_uv = {}
                    for i in range(4):
                        p = around_center(m, face_corner(face_index, i, lo0, hi0))
                        axes = [k for k in range(3) if DIRECTIONS[new_face][k] == 0]
                        for j in range(4):
                            q = face_corner(new_face, j, lo, hi)
                            if all(abs(q[k] - p[k]) < 1e-4 for k in axes) and j not in corner_uv:
                                corner_uv[j] = vertex_uv(uv, rot, i)
                                break
                    if len(corner_uv) < 4:
                        warnings.add(f"{block}: unmatched face corners")
                        continue
                face_tint = tint if "tintindex" in spec else (255, 255, 255)
                faces[new_face] = (ref, corner_uv, light, face_tint)
            if any(faces):
                elements.append({"lo": lo, "hi": hi, "spin": spin, "pivot": pivot, "faces": faces,
                                 "translucent": translucent, "elem_r": elem_r})
    return elements


SIGN_SUFFIXES = ("_wall_hanging_sign", "_hanging_sign", "_wall_sign", "_sign")
FACING_YAW = {"south": 0.0, "west": 90.0, "north": 180.0, "east": 270.0}
SIGN_THICKNESS = 2.0 * 2.0 / 3.0


def block_exists(client, block):
    return f"assets/minecraft/blockstates/{block}.json" in client.names


def sign_pieces(client, block, props):
    """PlaneChase SignBoardMapper pieces: (block, x, y, z, sx, sy, sz) in pixels of the sign frame."""
    wood = next((block[:-len(s)] for s in SIGN_SUFFIXES if block.endswith(s)), "oak")
    planks = f"{wood}_planks" if block_exists(client, f"{wood}_planks") else "oak_planks"
    if wood == "bamboo":
        stripped = "stripped_bamboo_block"
    elif block_exists(client, f"stripped_{wood}_log"):
        stripped = f"stripped_{wood}_log"
    elif block_exists(client, f"stripped_{wood}_stem"):
        stripped = f"stripped_{wood}_stem"
    else:
        stripped = "stripped_oak_log"
    chain = "iron_chain" if block_exists(client, "iron_chain") else "chain"
    t = SIGN_THICKNESS

    def chains(bottom, top):
        return [(chain, 3.5 - 4, bottom, -4, 8, top - bottom, 8), (chain, 12.5 - 4, bottom, -4, 8, top - bottom, 8)]

    if block.endswith("_wall_hanging_sign"):
        return [(stripped, 1, 0, -1, 14, 10, 2), *chains(10, 14), (stripped, 0, 14, -2, 16, 2, 4)]
    if block.endswith("_hanging_sign"):
        return [(stripped, 1, 0, -1, 14, 10, 2), *chains(10, 16)]
    if block.endswith("_wall_sign"):
        return [(planks, 0, 4.33, -7 - t * 0.5, 16, 8, t)]
    return [(planks, 0, 9.33, -t * 0.5, 16, 8, t), (stripped, 7.33, 0, -t * 0.5, t, 9.33, t)]


def sign_yaw(props):
    if "facing" in props:
        return FACING_YAW.get(props["facing"], 0.0)
    return int(props.get("rotation", 0)) * 22.5


def bake_sign(client, block, props, warnings):
    yaw = sign_yaw(props)
    elements = []
    for piece_block, x, y, z, sx, sy, sz in sign_pieces(client, block, props):
        parts = parts_of(client, piece_block, {"axis": "y", "waterlogged": "false"})
        if not parts:
            warnings.add(f"{block}: piece {piece_block} has no model")
            continue
        textures, model_elements = client.model(parts[0]["model"])
        scale = (sx / 16.0, sy / 16.0, sz / 16.0)
        offset = (x - 8.0, y, z)

        def frame(p):
            return [offset[k] + scale[k] * p[k] for k in range(3)]

        for element in model_elements:
            lo0, hi0 = element["from"], element["to"]
            rotation = element.get("rotation")
            elem_angle = 0.0
            origin = [0.0, 0.0, 0.0]
            if rotation and rotation.get("angle", 0):
                if rotation["axis"] != "y":
                    warnings.add(f"{block}: piece rotation about {rotation['axis']} dropped")
                else:
                    elem_angle = rotation["angle"]
                    origin = frame(rotation.get("origin", [8, 8, 8]))
            theta = -yaw + elem_angle
            yaw_m = element_matrix(1, -yaw)
            moved = mat_vec(yaw_m, origin)
            shift = [moved[k] - origin[k] for k in range(3)]
            box_lo = [frame(lo0)[k] + shift[k] for k in range(3)]
            box_hi = [frame(hi0)[k] + shift[k] for k in range(3)]
            quarter_turns = round(theta / 90.0)
            rest = theta - 90.0 * quarter_turns
            m = rot_y(90 * quarter_turns)
            pivot = moved

            def turn(p):
                q = mat_vec(m, [p[k] - pivot[k] for k in range(3)])
                return [round(q[k] + pivot[k], 6) for k in range(3)]

            corners = [turn([box_hi[0] if i & 1 else box_lo[0], box_hi[1] if i & 2 else box_lo[1],
                             box_hi[2] if i & 4 else box_lo[2]]) for i in range(8)]
            lo = [min(c[k] for c in corners) for k in range(3)]
            hi = [max(c[k] for c in corners) for k in range(3)]
            elem_r = element_matrix(1, rest)
            faces = [None] * 6
            for face_index, name in enumerate(FACES):
                spec = element.get("faces", {}).get(name)
                if spec is None:
                    continue
                ref = spec.get("texture", "")
                seen = 0
                while ref.startswith("#") and seen < 16:
                    ref = textures.get(ref[1:], "")
                    seen += 1
                if not ref or ref.startswith("#") or client.texture(ref) is None:
                    continue
                new_face = direction_index(mat_vec(m, DIRECTIONS[face_index]))
                light = direction_index(mat_vec(element_matrix(1, theta), DIRECTIONS[face_index]))
                uv = spec.get("uv") or default_uv(lo0, hi0, face_index)
                rot = spec.get("rotation", 0)
                corner_uv = {}
                axes = [k for k in range(3) if DIRECTIONS[new_face][k] == 0]
                for i in range(4):
                    p = turn([box_hi[k] if FACE_INFO[face_index * 4 + i][k] else box_lo[k] for k in range(3)])
                    for j in range(4):
                        q = face_corner(new_face, j, lo, hi)
                        if j not in corner_uv and all(abs(q[k] - p[k]) < 1e-4 for k in axes):
                            corner_uv[j] = vertex_uv(uv, rot, i)
                            break
                if len(corner_uv) < 4:
                    warnings.add(f"{block}: unmatched sign face corners")
                    continue
                faces[new_face] = (ref, corner_uv, light, (255, 255, 255))
            if not any(faces):
                continue
            center = [8.0, 0.0, 8.0]
            spin = (2, round(rest * 2) + 128, 0) if abs(rest) > 1e-6 else (0, 128, 0)
            elements.append({"lo": [lo[k] + center[k] for k in range(3)], "hi": [hi[k] + center[k] for k in range(3)],
                             "spin": spin, "pivot": [pivot[k] + center[k] for k in range(3)] if spin[0] else [8, 8, 8],
                             "faces": faces, "translucent": False,
                             "elem_r": elem_r if spin[0] else [[1, 0, 0], [0, 1, 0], [0, 0, 1]]})
    return elements


def element_bounds(element):
    lo, hi = element["lo"], element["hi"]
    if element["spin"][0] == 0:
        return lo, hi
    r = element["elem_r"]
    scale = [1.0, 1.0, 1.0]
    if element["spin"][2]:
        for i in range(3):
            col = [abs(r[k][i]) for k in range(3)]
            scale[i] = 1.0 / max(col)
    pts = []
    for i in range(8):
        p = [hi[0] if i & 1 else lo[0], hi[1] if i & 2 else lo[1], hi[2] if i & 4 else lo[2]]
        d = [(p[k] - element["pivot"][k]) * scale[k] for k in range(3)]
        q = mat_vec(r, d)
        pts.append([q[k] + element["pivot"][k] for k in range(3)])
    return [min(p[k] for p in pts) for k in range(3)], [max(p[k] for p in pts) for k in range(3)]


def coord12(value):
    encoded = round((value + 16) * 64)
    if not 0 <= encoded < 4096:
        raise ValueError(f"coordinate {value} outside the palette range")
    return encoded


def pack12(values):
    bits = 0
    for v in values:
        bits = (bits << 12) | coord12(v)
    width = 12 * len(values)
    pad = (-width) % 24
    bits <<= pad
    nbytes = (width + pad) // 8
    data = bits.to_bytes(nbytes, "big")
    return [(data[i], data[i + 1], data[i + 2], 255) for i in range(0, nbytes, 3)]


def encode(elements, tile_of, client):
    texels = []
    for element in elements:
        texels += pack12([*element["lo"], *element["hi"]])
        axis, angle, rescale = element["spin"]
        faces = element["faces"]
        mask = sum(1 << i for i, f in enumerate(faces) if f)
        opaque = not element["translucent"] and all(
            all(px[3] == 255 for px in client.texture(f[0])) for f in faces if f)
        flags = axis | (rescale << 2) | ((1 if element["translucent"] else 0) << 3) | ((1 if opaque else 0) << 4)
        texels.append((flags, angle, mask, 255))
        texels += pack12(element["pivot"])
        for face in faces:
            if face is None:
                texels += [(0, 0, 0, 255)] * 4
                continue
            ref, corner_uv, light, tint = face
            tile = tile_of(ref)
            u0, v0 = corner_uv[0]
            u3, v3 = corner_uv[3]
            u1, v1 = corner_uv[1]
            texels += [(tile >> 8, tile & 255, light, 255), (uv8(u0), uv8(v0), uv8(u3), 255),
                       (uv8(v3), uv8(u1), uv8(v1), 255), (*tint, 255)]
        assert len(texels) % ELEMENT_TEXELS == 0
    return tuple(texels)


def full_cube(elements):
    if len(elements) != 1:
        return False
    e = elements[0]
    return e["lo"] == [0, 0, 0] and e["hi"] == [16, 16, 16] and not e["spin"][0] and all(e["faces"])


def opaque_full_cube(elements, client):
    if len(elements) != 1:
        return False
    e = elements[0]
    if e["lo"] != [0, 0, 0] or e["hi"] != [16, 16, 16] or e["spin"][0] or e["translucent"]:
        return False
    for face in e["faces"]:
        if face is None or any(px[3] != 255 for px in client.texture(face[0])):
            return False
    return True


def normalise(block, props):
    if not props:
        return f"minecraft:{block}"
    return f"minecraft:{block}[" + ",".join(f"{k}={props[k]}" for k in sorted(props)) + "]"


def group_model(gx, gy, gz, rows):
    elements = []
    for dx in range(2):
        for dy in range(2):
            for dz in range(2):
                cx, cy, cz = 2 * gx + dx, 2 * gy + dy, 2 * gz + dz
                faces = {}
                for face, name in enumerate(FACES):
                    left = 16 * (face + 1)
                    faces[name] = {
                        "uv": [round((left + 0.5) * 16 / SPRITE_W, 6), round(0.5 * 16 / rows, 6),
                               round((left + 15.5) * 16 / SPRITE_W, 6), round(15.5 * 16 / rows, 6)],
                        "texture": "#p", "tintindex": dx * 4 + dy * 2 + dz}
                elements.append({"from": [cx - 16, cy - 16, cz - 16], "to": [cx - 15, cy - 15, cz - 15],
                                 "faces": faces})
    return {"textures": {"p": f"{NS}:block/canvas_palette", "particle": f"{NS}:block/canvas_palette"},
            "elements": elements}


def tile_item(size):
    sx, sy, sz = size
    gxn, gyn, gzn = sx // 2, sy // 2, sz // 2
    entries = []
    for gx in range(gxn):
        for gy in range(gyn):
            for gz in range(gzn):
                g = (gx * gyn + gy) * gzn + gz
                entries.append({
                    "type": "minecraft:condition", "property": "minecraft:custom_model_data", "index": g,
                    "on_true": {"type": "minecraft:model", "model": f"{NS}:canvas/g_{gx}_{gy}_{gz}",
                                "tints": [{"type": "minecraft:custom_model_data", "index": 8 * g + k, "default": 0}
                                          for k in range(8)]},
                    "on_false": {"type": "minecraft:empty"}})
    return {"model": {"type": "minecraft:composite", "models": entries}}


def main(argv):
    jar, blocks_json, pack_out, shapes_out = argv[1:5]
    iris_dir = argv[argv.index("--iris") + 1] if "--iris" in argv else None
    client = Client(jar)
    tints = Tints(client)
    report = json.loads(Path(blocks_json).read_text())
    warnings = set()
    shape_ids = {}
    shapes = []
    table = {}
    rejected = 0
    for block_id, info in sorted(report.items()):
        block = block_id.removeprefix("minecraft:")
        for state in info["states"]:
            props = state.get("properties", {})
            if block.endswith("_sign"):
                elements = bake_sign(client, block, props, warnings)
            else:
                elements = bake_state(client, tints, block, props, warnings)
            if not elements:
                continue
            if len(elements) > MAX_ELEMENTS:
                rejected += 1
                continue
            key = json.dumps([[e["lo"], e["hi"], e["spin"], e["pivot"], e["translucent"],
                               [None if f is None else [f[0], sorted(f[1].items()), f[2], f[3]] for f in e["faces"]]]
                              for e in elements], sort_keys=True)
            if key not in shape_ids:
                shape_ids[key] = len(shapes) + 1
                shapes.append(elements)
            sid = shape_ids[key]
            table[normalise(block, props)] = {"id": sid, "opaqueFullCube": opaque_full_cube(elements, client),
                                              "translucent": elements[0]["translucent"]}
    if len(shapes) >= 32767:
        raise SystemExit("too many shapes for 15 bits")

    tiles = []
    tile_index = {}

    def tile_of(ref):
        if ref not in tile_index:
            tile_index[ref] = len(tiles)
            tiles.append(ref)
        return tile_index[ref]

    element_texels = []
    headers = {}
    for sid, elements in enumerate(shapes, start=1):
        bounds = [element_bounds(e) for e in elements]
        lo = [min(b[0][k] for b in bounds) for k in range(3)]
        hi = [max(b[1][k] for b in bounds) for k in range(3)]
        headers[sid] = (len(element_texels) // ELEMENT_TEXELS, len(elements), lo, hi, full_cube(elements))
        element_texels += encode(elements, tile_of, client)

    header_rows = math.ceil(SHAPE_TEXELS * (len(shapes) + 1) / SPRITE_W)
    element_row = 16 * math.ceil((SHAPE_ROW + header_rows) / 16)
    element_rows = 16 * math.ceil(math.ceil(len(element_texels) / SPRITE_W) / 16)
    texture_row = element_row + element_rows
    rows = texture_row + 16 * math.ceil(len(tiles) / 16)
    if max(element_row, texture_row) >= 65536 or len(element_texels) // ELEMENT_TEXELS >= 65536:
        raise SystemExit("palette too large")
    sprite = [(0, 0, 0, 255)] * (SPRITE_W * rows)

    def put(x, y, rgba):
        sprite[y * SPRITE_W + x] = rgba

    put(0, 0, MARKER)
    put(1, 0, (element_row >> 8, element_row & 255, 0, 255))
    put(2, 0, (texture_row >> 8, texture_row & 255, FORMAT, 255))
    for face in range(6):
        for py in range(16):
            for px in range(16):
                x = 16 * (face + 1) + px
                put(x, py, (x, py, face + 1, 255))
    for sid, (start, count, lo, hi, full) in headers.items():
        base = SHAPE_TEXELS * sid
        texels = [(start >> 8, start & 255, count, 255),
                  (box_byte(lo[0], False), box_byte(lo[1], False), box_byte(lo[2], False), 255),
                  (box_byte(hi[0], True), box_byte(hi[1], True), box_byte(hi[2], True), 255),
                  (1 if full else 0, 0, 0, 255)]
        for k, rgba in enumerate(texels):
            put((base + k) % SPRITE_W, SHAPE_ROW + (base + k) // SPRITE_W, rgba)
    for index, rgba in enumerate(element_texels):
        put(index % SPRITE_W, element_row + index // SPRITE_W, rgba)
    if not all(px[3] == 255 for px in sprite[:SPRITE_W * texture_row]):
        raise SystemExit("data texels must stay opaque")
    for tile, ref in enumerate(tiles):
        ox, oy = 16 * (tile % 16), texture_row + 16 * (tile // 16)
        for i, rgba in enumerate(client.texture(ref)):
            put(ox + i % 16, oy + i // 16, rgba)

    glsl = (HERE / "pcanvas.glsl").read_bytes()
    with zipfile.ZipFile(pack_out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("pack.mcmeta", json.dumps({"pack": {
            "description": "PlaneChase head canvas (palette format 4)",
            "pack_format": 69, "min_format": 69, "max_format": 75}}, indent=2))
        buffer = io.BytesIO()
        image = Image.new("RGBA", (SPRITE_W, rows))
        image.putdata(sprite)
        image.save(buffer, "PNG", optimize=True)
        z.writestr(f"assets/{NS}/textures/block/canvas_palette.png", buffer.getvalue())
        sep = (",", ":")
        for gx in range(MAX_TILE[0] // 2):
            for gy in range(MAX_TILE[1] // 2):
                for gz in range(MAX_TILE[2] // 2):
                    z.writestr(f"assets/{NS}/models/canvas/g_{gx}_{gy}_{gz}.json",
                               json.dumps(group_model(gx, gy, gz, rows), separators=sep))
        for size in TILE_LADDER:
            z.writestr(f"assets/{NS}/items/canvas_{size[0]}x{size[1]}x{size[2]}.json",
                       json.dumps(tile_item(size), separators=sep))
        z.writestr(f"assets/{NS}/shaders/include/pcanvas.glsl", glsl)
        for ext in ("vsh", "fsh"):
            z.write(HERE / f"item_translucent_cull.{ext}",
                    f"assets/minecraft/shaders/core/rendertype_item_entity_translucent_cull.{ext}")
    for old, new in RENAMED.items():
        for key in [k for k in table if k == f"minecraft:{new}" or k.startswith(f"minecraft:{new}[")]:
            table[f"minecraft:{old}" + key[len(f"minecraft:{new}"):]] = table[key]
    Path(shapes_out).write_text(json.dumps({"format": 1, "palette": FORMAT, "shapes": table},
                                           separators=(",", ":"), sort_keys=True))
    if iris_dir:
        Path(iris_dir, "pcanvas_core.glsl").write_bytes(glsl)
    for w in sorted(warnings)[:40]:
        print("warning:", w)
    print(f"{len(table)} states -> {len(shapes)} shapes, {len(element_texels) // ELEMENT_TEXELS} elements, "
          f"{len(tiles)} textures, {rejected} states over {MAX_ELEMENTS} elements, sprite {SPRITE_W}x{rows}, "
          f"{len(warnings)} warnings")


if __name__ == "__main__":
    main(sys.argv)

// PlaneChase head canvas decoder, palette format 2. Shared verbatim by the vanilla core shader
// (assets/planechase/shaders/include/pcanvas.glsl, #moj_import <planechase:pcanvas.glsl>) and the
// Iris shader pack (shaders/lib/pcanvas_core.glsl). Pure functions only: no inputs, outputs or
// uniforms, so each host declares its own varyings. Written by canvas_gen.py; edit it there.
//
// Palette sprite (block atlas, read with texelFetch at mip 0; every data texel has alpha 255):
//   (0,0) marker 80,67,86,255; (1,0) element row; (2,0) texture row (r,g = 16-bit row).
//   x 16..111, rows 0..15: six face-header tiles, pixel = (x - marker.x, y - marker.y, face + 1).
//   row 16..: three texels per shape id s at linear index 3s: (start hi, start lo, element count),
//     (bbox min x, y, z), (bbox max x, y, z), bbox byte b = model pixel b / 4 - 16 (floor / ceil).
//   element rows: 32 texels per element: 0-5 from, to, pivot (16-bit fixed, value / 256 - 16),
//     6 rotation (axis 1..3, angle * 2 + 128, rescale), 7 (face mask, flags bit0 translucent),
//     8 + 4f per face f: (tile hi, tile lo, light dir), (u0, v0, u3), (v3, u1, v1), (tint r, g, b)
//     with u/v at face corners 0, 1, 3 in 1/16 texel (255 = 16).
//   texture rows: 16x16 tiles, 16 per row.
// Cell word (vertex colour, 24 bits): shape id bits 0-14, occluded face mask bits 15-20 (down, up,
// north, south, west, east), debug mode bits 21-23. Proxy cubes face outward.

#ifndef PCANVAS_GLSL
#define PCANVAS_GLSL

const ivec4 PC_MARKER = ivec4(80, 67, 86, 255);
const int PC_ELEMENT_TEXELS = 32;
const int PC_MAX_ELEMENTS = 32;
const int PC_SHAPE_ROW = 16;
const int PCANVAS_NONE = 0;
const int PCANVAS_VISIBLE = 1;
const int PCANVAS_HIDDEN = 2;

const ivec3 PC_FACE_INFO[24] = ivec3[24](
    ivec3(0, 0, 1), ivec3(0, 0, 0), ivec3(1, 0, 0), ivec3(1, 0, 1),
    ivec3(0, 1, 0), ivec3(0, 1, 1), ivec3(1, 1, 1), ivec3(1, 1, 0),
    ivec3(1, 1, 0), ivec3(1, 0, 0), ivec3(0, 0, 0), ivec3(0, 1, 0),
    ivec3(0, 1, 1), ivec3(0, 0, 1), ivec3(1, 0, 1), ivec3(1, 1, 1),
    ivec3(0, 1, 0), ivec3(0, 0, 0), ivec3(0, 0, 1), ivec3(0, 1, 1),
    ivec3(1, 1, 1), ivec3(1, 0, 1), ivec3(1, 0, 0), ivec3(1, 1, 0)
);
const vec3 PC_DIRECTIONS[6] = vec3[6](
    vec3(0, -1, 0), vec3(0, 1, 0), vec3(0, 0, -1), vec3(0, 0, 1), vec3(-1, 0, 0), vec3(1, 0, 0)
);

ivec4 pcTexel(sampler2D atlas, ivec2 p) {
    return ivec4(texelFetch(atlas, p, 0) * 255.0 + 0.5);
}

ivec4 pcAt(sampler2D atlas, ivec2 origin, int row, int index) {
    return pcTexel(atlas, origin + ivec2(index % 256, row + index / 256));
}

int pcanvasVertex(sampler2D atlas, vec2 uv0, vec4 color, out int shape, out int mode, out int face,
        out ivec2 origin, out vec3 local) {
    shape = 0;
    mode = 0;
    face = 0;
    origin = ivec2(0);
    local = vec3(0.0);
    ivec2 atlasSize = textureSize(atlas, 0);
    vec2 uvPx = uv0 * vec2(atlasSize);
    ivec2 px = ivec2(uvPx);
    if (px.x < 0 || px.y < 0 || px.x >= atlasSize.x || px.y >= atlasSize.y) {
        return PCANVAS_NONE;
    }
    ivec4 h = pcTexel(atlas, px);
    ivec2 tl = px - h.rg;
    if (h.a != 255 || h.b < 1 || h.b > 6 || tl.x < 0 || tl.y < 0 || pcTexel(atlas, tl) != PC_MARKER) {
        return PCANVAS_NONE;
    }
    face = h.b - 1;
    ivec3 c = ivec3(color.rgb * 255.0 + 0.5);
    int word = (c.r << 16) | (c.g << 8) | c.b;
    shape = word & 0x7FFF;
    int mask = (word >> 15) & 63;
    mode = (word >> 21) & 7;
    if (shape == 0 || ((mask >> face) & 1) != 0) {
        shape = 0;
        return PCANVAS_HIDDEN;
    }
    vec2 corner = step(vec2(8.0), uvPx - vec2(tl) - vec2(float(16 * (face + 1)), 0.0));
    int vertex = corner.x < 0.5 ? (corner.y < 0.5 ? 0 : 1) : (corner.y < 0.5 ? 3 : 2);
    local = vec3(PC_FACE_INFO[face * 4 + vertex]);
    origin = tl;
    return PCANVAS_VISIBLE;
}

float pcCoord(int hi, int lo) {
    return float(hi * 256 + lo) / 256.0 - 16.0;
}

float pcUv(int v) {
    return v == 255 ? 16.0 : float(v) / 16.0;
}

mat3 pcRotation(int axis, float angle) {
    float c = cos(angle);
    float s = sin(angle);
    if (axis == 1) return mat3(1, 0, 0, 0, c, s, 0, -s, c);
    if (axis == 2) return mat3(c, 0, -s, 0, 1, 0, s, 0, c);
    return mat3(c, s, 0, -s, c, 0, 0, 0, 1);
}

vec3 pcCorner(int face, int vertex, vec3 lo, vec3 hi) {
    ivec3 e = PC_FACE_INFO[face * 4 + vertex];
    return vec3(e.x == 1 ? hi.x : lo.x, e.y == 1 ? hi.y : lo.y, e.z == 1 ? hi.z : lo.z);
}

vec2 pcSlab(vec3 o, vec3 invD, vec3 lo, vec3 hi) {
    vec3 ta = (lo - o) * invD;
    vec3 tb = (hi - o) * invD;
    vec3 tNear = min(ta, tb);
    vec3 tFar = max(ta, tb);
    return vec2(max(max(tNear.x, tNear.y), tNear.z), min(min(tFar.x, tFar.y), tFar.z));
}

// Rebuilds the proxy face's cell-to-model basis from the screen-space derivatives (the face is
// planar, so the map is affine) and returns false when it is degenerate.
bool pcanvasBasis(int face, vec3 dpdx, vec3 dpdy, vec3 dldx, vec3 dldy, out mat3 basis) {
    int k = face < 2 ? 1 : (face < 4 ? 2 : 0);
    int u = (k + 1) % 3;
    int v = (k + 2) % 3;
    mat2 inPlane = mat2(dldx[u], dldx[v], dldy[u], dldy[v]);
    basis = mat3(1.0);
    if (abs(determinant(inPlane)) < 1e-12) {
        return false;
    }
    mat2 inv = inverse(inPlane);
    vec3 au = dpdx * inv[0][0] + dpdy * inv[0][1];
    vec3 av = dpdx * inv[1][0] + dpdy * inv[1][1];
    float scale = 0.5 * (length(au) + length(av));
    basis[u] = au;
    basis[v] = av;
    basis[k] = cross(au, av) / scale;
    return true;
}

// Casts the eye ray (camera and view are in the vertex position space) through the shape's
// elements inside the cell; returns the nearest texel hit (alpha 1 unless the element is
// translucent, cutout 0.1), its position in vertex space and its snapped lighting normal.
bool pcanvasTrace(sampler2D atlas, int shape, ivec2 origin, vec3 local, vec3 view, vec3 camera, mat3 basis,
        out vec4 albedo, out vec3 hitPos, out vec3 hitNormal) {
    albedo = vec4(0.0);
    hitPos = view;
    hitNormal = vec3(0.0, 1.0, 0.0);
    mat3 toLocal = inverse(basis);
    vec3 dir = normalize(view - camera);
    vec3 rayOrigin = (local + toLocal * (camera - view)) * 16.0;
    vec3 rayDir = (toLocal * dir) * 16.0;

    ivec4 shapeHeader = pcAt(atlas, origin, PC_SHAPE_ROW, 3 * shape);
    ivec4 boxLo = pcAt(atlas, origin, PC_SHAPE_ROW, 3 * shape + 1);
    ivec4 boxHi = pcAt(atlas, origin, PC_SHAPE_ROW, 3 * shape + 2);
    vec2 box = pcSlab(rayOrigin, 1.0 / rayDir, vec3(boxLo.rgb) / 4.0 - 16.0, vec3(boxHi.rgb) / 4.0 - 16.0);
    if (box.x > box.y || box.y < 0.0) {
        return false;
    }

    int elementRow = pcAt(atlas, origin, 0, 1).r * 256 + pcAt(atlas, origin, 0, 1).g;
    int textureRow = pcAt(atlas, origin, 0, 2).r * 256 + pcAt(atlas, origin, 0, 2).g;
    int start = shapeHeader.r * 256 + shapeHeader.g;
    int count = min(shapeHeader.b, PC_MAX_ELEMENTS);

    float bestT = 1e30;
    vec4 bestColor = vec4(0.0);
    int bestLight = 1;
    for (int e = 0; e < PC_MAX_ELEMENTS; e++) {
        if (e >= count) break;
        int base = (start + e) * PC_ELEMENT_TEXELS;
        ivec4 t0 = pcAt(atlas, origin, elementRow, base);
        ivec4 t1 = pcAt(atlas, origin, elementRow, base + 1);
        ivec4 t2 = pcAt(atlas, origin, elementRow, base + 2);
        ivec4 t3 = pcAt(atlas, origin, elementRow, base + 3);
        ivec4 t4 = pcAt(atlas, origin, elementRow, base + 4);
        ivec4 t5 = pcAt(atlas, origin, elementRow, base + 5);
        ivec4 spin = pcAt(atlas, origin, elementRow, base + 6);
        ivec4 flags = pcAt(atlas, origin, elementRow, base + 7);
        vec3 lo = vec3(pcCoord(t0.r, t0.g), pcCoord(t0.b, t1.r), pcCoord(t1.g, t1.b));
        vec3 hi = vec3(pcCoord(t2.r, t2.g), pcCoord(t2.b, t3.r), pcCoord(t3.g, t3.b));
        vec3 pivot = vec3(pcCoord(t4.r, t4.g), pcCoord(t4.b, t5.r), pcCoord(t5.g, t5.b));
        bool translucent = (flags.g & 1) != 0;

        vec3 o = rayOrigin;
        vec3 d = rayDir;
        if (spin.r != 0) {
            mat3 r = pcRotation(spin.r, radians(float(spin.g - 128) * 0.5));
            vec3 s = vec3(1.0);
            if (spin.b == 1) {
                for (int i = 0; i < 3; i++) {
                    vec3 col = abs(r[i]);
                    s[i] = 1.0 / max(max(col.x, col.y), col.z);
                }
            }
            mat3 undo = mat3(1.0 / s.x, 0, 0, 0, 1.0 / s.y, 0, 0, 0, 1.0 / s.z) * transpose(r);
            o = undo * (o - pivot) + pivot;
            d = undo * d;
        }

        vec3 invD = 1.0 / d;
        vec3 ta = (lo - o) * invD;
        vec3 tb = (hi - o) * invD;
        vec3 tNear = min(ta, tb);
        float tEnter = max(max(tNear.x, tNear.y), tNear.z);
        float tExit = min(min(max(ta.x, tb.x), max(ta.y, tb.y)), max(ta.z, tb.z));
        if (tEnter > tExit + 1e-4 || tEnter < 0.0 || tEnter >= bestT) continue;

        int axis = tNear.x >= tNear.y && tNear.x >= tNear.z ? 0 : (tNear.y >= tNear.z ? 1 : 2);
        int face = axis == 0 ? (d.x > 0.0 ? 4 : 5) : (axis == 1 ? (d.y > 0.0 ? 0 : 1) : (d.z > 0.0 ? 2 : 3));
        if ((flags.r & (1 << face)) == 0) continue;

        int fb = base + 8 + face * 4;
        ivec4 fa = pcAt(atlas, origin, elementRow, fb);
        ivec4 fu = pcAt(atlas, origin, elementRow, fb + 1);
        ivec4 fv = pcAt(atlas, origin, elementRow, fb + 2);
        ivec4 ft = pcAt(atlas, origin, elementRow, fb + 3);
        vec3 p = clamp(o + tEnter * d, lo, hi);
        vec3 v0 = pcCorner(face, 0, lo, hi);
        vec3 e3 = pcCorner(face, 3, lo, hi) - v0;
        vec3 e1 = pcCorner(face, 1, lo, hi) - v0;
        float s3 = clamp(dot(e3, e3) > 0.0 ? dot(p - v0, e3) / dot(e3, e3) : 0.0, 0.0, 1.0);
        float s1 = clamp(dot(e1, e1) > 0.0 ? dot(p - v0, e1) / dot(e1, e1) : 0.0, 0.0, 1.0);
        vec2 uv0 = vec2(pcUv(fu.r), pcUv(fu.g));
        vec2 uv3 = vec2(pcUv(fu.b), pcUv(fv.r));
        vec2 uv1 = vec2(pcUv(fv.g), pcUv(fv.b));
        vec2 uv2 = uv3 + uv1 - uv0;
        vec2 uv = uv0 + s3 * (uv3 - uv0) + s1 * (uv1 - uv0);
        vec2 uvMin = min(min(uv0, uv1), min(uv2, uv3)) + 1e-3;
        vec2 uvMax = max(uvMin, max(max(uv0, uv1), max(uv2, uv3)) - 1e-3);
        ivec2 texel = clamp(ivec2(floor(clamp(uv, uvMin, uvMax))), ivec2(0), ivec2(15));
        int tile = fa.r * 256 + fa.g;
        vec4 color = texelFetch(atlas, origin + ivec2(16 * (tile % 16), textureRow + 16 * (tile / 16)) + texel, 0);
        if (color.a < 0.1) continue;
        if (!translucent) color.a = 1.0;
        color.rgb *= vec3(ft.rgb) / 255.0;
        bestT = tEnter;
        bestColor = color;
        bestLight = fa.b;
    }
    if (bestT >= 1e29) {
        return false;
    }
    albedo = bestColor;
    hitPos = camera + dir * bestT;
    hitNormal = normalize(basis * PC_DIRECTIONS[bestLight]);
    return true;
}

#endif

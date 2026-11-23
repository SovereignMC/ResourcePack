#version 330

// Vanilla rendertype_item_entity_translucent_cull (1.21.8 - 1.21.11) + the SovereignMC gun
// viewmodel decoder ("sgvm"). Derived from objmc by Godlander (MIT, see LICENSE-OBJMC):
// the face-header / topleft-marker trick, first-person hand detection and the camera-space
// offset are objmc's. The data layout is our own skeletal variant: static per-vertex rest
// positions + one 3x4 matrix per bone per tick, written by tools/generate/guns/viewmodel_bake.py.
//
// Only item models whose texture carries the sgvm marker are affected, and only in the
// first-person hand. Everything else renders exactly like vanilla.

#moj_import <minecraft:light.glsl>
#moj_import <minecraft:fog.glsl>
#moj_import <minecraft:dynamictransforms.glsl>
#moj_import <minecraft:projection.glsl>
#moj_import <minecraft:globals.glsl>

in vec3 Position;
in vec4 Color;
in vec2 UV0;
in vec2 UV1;
in ivec2 UV2;
in vec3 Normal;

uniform sampler2D Sampler0;
uniform sampler2D Sampler2;

out float sphericalVertexDistance;
out float cylindricalVertexDistance;
out vec4 vertexColor;
out vec2 texCoord0;
out vec2 texCoord1;
out vec2 texCoord2;
out vec4 sgvmLight;
out vec3 sgvmPos;
flat out int sgvmGun;

ivec4 sgvmTexel(ivec2 p) {
    return ivec4(texelFetch(Sampler0, p, 0) * 255.0 + 0.5);
}

// pixel at linear index i of a block of rows starting at `row`, `w` pixels wide
ivec4 sgvmAt(ivec2 tl, int w, int row, int i) {
    return sgvmTexel(tl + ivec2(i % w, row + i / w));
}

float sgvmFixed(ivec4 c) {
    return float(c.r * 65536 + c.g * 256 + c.b - 8388608) / 65536.0;
}

// first person hand item projection (objmc, "Balint nonsense": near plane 0.05)
bool sgvmIsHand(mat4 proj) {
    return abs(proj[3][2] + 0.10005) < 0.00001;
}

vec3 sgvmBone(ivec2 tl, int w, int row, int frame, int nbones, int bone, vec3 p) {
    int base = (frame * nbones + bone) * 12;
    float m[12];
    for (int j = 0; j < 12; j++) {
        m[j] = sgvmFixed(sgvmAt(tl, w, row, base + j));
    }
    return vec3(
        m[0] * p.x + m[1] * p.y + m[2] * p.z + m[9],
        m[3] * p.x + m[4] * p.y + m[5] * p.z + m[10],
        m[6] * p.x + m[7] * p.y + m[8] * p.z + m[11]
    );
}

void main() {
    vec3 pos = Position;
    texCoord0 = UV0;
    texCoord1 = UV1;
    texCoord2 = UV2;
    sgvmGun = 0;
    sgvmLight = texelFetch(Sampler2, UV2 / 16, 0);
    vertexColor = minecraft_mix_light(Light0_Direction, Light1_Direction, Normal, Color) * sgvmLight;

    if (sgvmIsHand(ProjMat)) {
        ivec2 atlas = textureSize(Sampler0, 0);
        ivec2 uv = ivec2(UV0 * vec2(atlas));
        ivec4 h = sgvmTexel(uv);
        ivec2 tl = uv - ivec2(h.r * 256 + h.g, h.b * 256 + h.a);
        if (tl.x >= 0 && tl.y >= 0 && tl.x < atlas.x && tl.y < atlas.y
                && sgvmTexel(tl) == ivec4(83, 71, 86, 77)) {
            // header: 1 = (width, texture height), 2 = (vertex count, bone count),
            //         3 = (texture row, vertex row), 4 = (frame row, animation count)
            ivec4 m1 = sgvmTexel(tl + ivec2(1, 0));
            ivec4 m2 = sgvmTexel(tl + ivec2(2, 0));
            ivec4 m3 = sgvmTexel(tl + ivec2(3, 0));
            ivec4 m4 = sgvmTexel(tl + ivec2(4, 0));
            int w = m1.r * 256 + m1.g;
            int texH = m1.b * 256 + m1.a;
            int nbones = m2.a;
            int rowTex = m3.r * 256 + m3.g;
            int rowVert = m3.b * 256 + m3.a;
            int rowFrame = m4.r * 256 + m4.g;
            int nanims = m4.b;

            // tint = animation control: r = paused bit | animation index, gb = tick value
            ivec3 tint = ivec3(Color.rgb * 255.0 + 0.5);
            bool paused = tint.r >= 128;
            int anim = tint.r & 127;
            float value = float(tint.g * 256 + tint.b);
            if (anim >= nanims) anim = 0;
            ivec4 entry = sgvmTexel(tl + ivec2(8 + anim, 0));
            if (entry.b == 0) entry = sgvmTexel(tl + ivec2(8 + 2, 0)); // missing -> standing
            int start = entry.r * 256 + entry.g;
            int frames = max(entry.b, 1);
            bool loop = (entry.a & 1) == 1;

            float t;
            if (paused) {
                t = value;
            } else {
                float dt = GameTime * 24000.0 - value;
                if (dt < -12000.0) dt += 24000.0; // the day counter wrapped since the start
                dt = max(dt, 0.0);                // client clock a little behind the server
                t = loop ? mod(dt, float(frames)) : dt;
            }
            t = loop ? t : min(t, float(frames - 1));
            int f0 = int(floor(t));
            float fr = t - float(f0);
            int f1 = f0 + 1;
            if (loop) {
                f0 = f0 % frames;
                f1 = f1 % frames;
            } else {
                f0 = min(f0, frames - 1);
                f1 = min(f1, frames - 1);
            }

            // static vertex: 5 pixels (x, y, z, bone|u, v)
            int vid = (((uv.y - tl.y - 1) * w) + (uv.x - tl.x)) * 4 + gl_VertexID % 4;
            int vbase = vid * 5;
            vec3 rest = vec3(
                sgvmFixed(sgvmAt(tl, w, rowVert, vbase)),
                sgvmFixed(sgvmAt(tl, w, rowVert, vbase + 1)),
                sgvmFixed(sgvmAt(tl, w, rowVert, vbase + 2))
            );
            ivec4 pu = sgvmAt(tl, w, rowVert, vbase + 3);
            ivec4 pv = sgvmAt(tl, w, rowVert, vbase + 4);
            int bone = pu.r;
            vec2 tuv = vec2(float(pu.g * 256 + pu.b), float(pv.g * 256 + pv.b)) / 65535.0;

            vec3 a = sgvmBone(tl, w, rowFrame, start + f0, nbones, bone, rest);
            vec3 b = sgvmBone(tl, w, rowFrame, start + f1, nbones, bone, rest);
            vec3 offset = mix(a, b, fr);

            // camera-space offset from the anchor (objmc): undo the model-view rotation so the
            // gun stays locked to the camera and only the anchor follows hand bob / swing.
            pos = Position + (vec4(offset, 0.0) * ModelViewMat).xyz;
            texCoord0 = (vec2(tl) + vec2(0.0, float(rowTex)) + tuv * vec2(float(w), float(texH))) / vec2(atlas);
            sgvmGun = 1;
        }
    }

    sgvmPos = pos;
    gl_Position = ProjMat * ModelViewMat * vec4(pos, 1.0);
    sphericalVertexDistance = fog_spherical_distance(pos);
    cylindricalVertexDistance = fog_cylindrical_distance(pos);
}

#version 330

// Vanilla core/entity (1.21.11 body) + SovereignMC first-person skinned arms. See entity.vsh.

#moj_import <minecraft:fog.glsl>
#moj_import <minecraft:dynamictransforms.glsl>

uniform sampler2D Sampler0;

in float sphericalVertexDistance;
in float cylindricalVertexDistance;
#ifdef PER_FACE_LIGHTING
in vec4 vertexPerFaceColorBack;
in vec4 vertexPerFaceColorFront;
#else
in vec4 vertexColor;
#endif
in vec4 lightMapColor;
in vec4 overlayColor;
in vec2 texCoord0;
flat in int sgarmFace;
in vec2 sgarmST;

out vec4 fragColor;

// Skin UV (pixels, 64x64) of an arm segment face. The head box is oriented like a vanilla
// player arm, so face f of the head is face f of the arm. Rects are (x1, y1, x2, y2) as in
// ModelPart.Polygon; the arm box is texOffs (40,16) w=4 h=12 d=4, the sleeve is 16 px lower.
// Mirrored layers (back-facing here) are the upper arm: upper half of the sides.
vec2 sgarmUV(int face, bool hat, vec2 st, bool upper) {
    int f = face % 6;
    vec4 r;
    if (f == 0) {
        r = vec4(44.0, 16.0, 48.0, 20.0);      // top cap
    } else if (f == 1) {
        r = vec4(48.0, 20.0, 52.0, 16.0);      // bottom cap (y swapped like vanilla)
    } else {
        float y1 = upper ? 20.0 : 26.0;
        float y2 = upper ? 26.0 : 32.0;
        float x1 = f == 2 ? 40.0 : (f == 3 ? 44.0 : (f == 4 ? 48.0 : 52.0));
        r = vec4(x1, y1, x1 + 4.0, y2);
    }
    vec2 p = mix(r.xy, r.zw, st);
    if (hat) {
        p.y += 16.0;
    }
    return p / 64.0;
}

void main() {
    vec2 uv0 = texCoord0;
    if (sgarmFace >= 0) {
        uv0 = sgarmUV(sgarmFace, sgarmFace >= 6, sgarmST, !gl_FrontFacing);
    }
    vec4 color = texture(Sampler0, uv0);
#ifdef ALPHA_CUTOUT
    if (color.a < ALPHA_CUTOUT) {
        discard;
    }
#endif
#ifdef PER_FACE_LIGHTING
    color *= (gl_FrontFacing ? vertexPerFaceColorFront : vertexPerFaceColorBack) * ColorModulator;
#else
    color *= vertexColor * ColorModulator;
#endif
#ifndef NO_OVERLAY
    color.rgb = mix(overlayColor.rgb, color.rgb, overlayColor.a);
#endif
#ifndef EMISSIVE
    color *= lightMapColor;
#endif
    fragColor = apply_fog(color, sphericalVertexDistance, cylindricalVertexDistance, FogEnvironmentalStart, FogEnvironmentalEnd, FogRenderDistanceStart, FogRenderDistanceEnd, FogColor);
}

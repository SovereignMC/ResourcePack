#version 330
#extension GL_ARB_derivative_control : enable
#extension GL_ARB_conservative_depth : enable

precision highp float;
precision highp int;
#ifdef GL_ARB_conservative_depth
layout(depth_greater) out float gl_FragDepth;
#endif
#ifdef GL_ARB_derivative_control
#define PC_DFDX dFdxFine
#define PC_DFDY dFdyFine
#else
#define PC_DFDX dFdx
#define PC_DFDY dFdy
#endif

// PlaneChase head canvas: a canvas proxy fragment ray casts its cell's shape (palette format 2,
// planechase:pcanvas.glsl), shades the hit like a block display and writes its depth; outward
// proxies keep the hit behind the face, so the write is depth_greater and early-z stays on.

// Vanilla rendertype_item_entity_translucent_cull + SovereignMC gun viewmodel lighting.
// Arm texels (sgvmGun == 2) take their colour from the tint and are shaded like the gun.
// See the .vsh for credits (objmc by Godlander, MIT).

#moj_import <minecraft:light.glsl>
#moj_import <minecraft:fog.glsl>
#moj_import <minecraft:dynamictransforms.glsl>
#moj_import <minecraft:projection.glsl>
#moj_import <planechase:pcanvas.glsl>

uniform sampler2D Sampler0;

in float sphericalVertexDistance;
in float cylindricalVertexDistance;
in vec4 vertexColor;
in vec2 texCoord0;
in vec2 texCoord1;
in vec4 sgvmLight;
in vec3 sgvmPos;
flat in int sgvmGun;
flat in vec4 sgvmColor;
flat in int pcShape;
flat in int pcMode;
flat in int pcFace;
flat in ivec2 pcOrigin;
in vec3 pcLocal;
in vec3 pcView;

out vec4 fragColor;

void main() {
    if (pcShape != 0) {
        if (pcShape < 0) {
            discard;
        }
        mat3 basis;
        if (!pcanvasBasis(pcFace, PC_DFDX(pcView), PC_DFDY(pcView), PC_DFDX(pcLocal), PC_DFDY(pcLocal), basis)) {
            discard;
        }
        if (pcMode == 1) {
            gl_FragDepth = gl_FragCoord.z;
            fragColor = vec4(pcLocal, 1.0);
            return;
        }
        vec3 camera = (inverse(ModelViewMat) * vec4(0.0, 0.0, 0.0, 1.0)).xyz;
        vec4 albedo;
        vec3 hit;
        vec3 normal;
        if (!pcanvasTrace(Sampler0, pcShape, pcOrigin, pcLocal, pcView, camera, basis, albedo, hit, normal)) {
            discard;
        }
        vec4 shaded = albedo * minecraft_mix_light(Light0_Direction, Light1_Direction, normal, vec4(1.0)) * sgvmLight * ColorModulator;
        vec4 clip = ProjMat * ModelViewMat * vec4(hit, 1.0);
        gl_FragDepth = max(gl_FragCoord.z, clip.z / clip.w * 0.5 + 0.5);
        fragColor = apply_fog(shaded, fog_spherical_distance(hit), fog_cylindrical_distance(hit), FogEnvironmentalStart, FogEnvironmentalEnd, FogRenderDistanceStart, FogRenderDistanceEnd, FogColor);
        return;
    }
    gl_FragDepth = gl_FragCoord.z;
    vec4 color = texture(Sampler0, texCoord0);
    if (sgvmGun == 2) {
        // skinned arm texel: flat colour from the tint (alpha 0 = transparent sleeve texel)
        if (sgvmColor.a < 0.5) {
            discard;
        }
        color = sgvmColor;
    }
    if (sgvmGun >= 1) {
        // flat face normal from the position derivatives (objmc)
        vec3 normal = normalize(cross(dFdx(sgvmPos), dFdy(sgvmPos)));
        color *= minecraft_mix_light(Light0_Direction, Light1_Direction, normal, vec4(1.0)) * sgvmLight;
    } else {
        color *= vertexColor;
    }
    color *= ColorModulator;
    if (color.a < 0.1) {
        discard;
    }
    fragColor = apply_fog(color, sphericalVertexDistance, cylindricalVertexDistance, FogEnvironmentalStart, FogEnvironmentalEnd, FogRenderDistanceStart, FogRenderDistanceEnd, FogColor);
}

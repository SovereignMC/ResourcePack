#version 330

// Vanilla rendertype_item_entity_translucent_cull + SovereignMC gun viewmodel lighting.
// Arm texels (sgvmGun == 2) take their colour from the tint and are shaded like the gun.
// See the .vsh for credits (objmc by Godlander, MIT).

#moj_import <minecraft:light.glsl>
#moj_import <minecraft:fog.glsl>
#moj_import <minecraft:dynamictransforms.glsl>

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

out vec4 fragColor;

void main() {
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

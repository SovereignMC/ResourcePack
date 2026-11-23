#version 330

// Vanilla core/entity (1.21.11 body; a superset of 1.21.8's, the PER_FACE_LIGHTING parts simply
// never apply there) + SovereignMC first-person skinned arms ("sgarm").
//
// The gun's first-person item model carries three extra `minecraft:player_head` composite
// layers (right forearm, left upper arm, left forearm). Each layer's base model display
// transform squeezes the 8x8x8 head box into one arm segment. Here the head/hat UV net is
// replaced by the skin's arm/sleeve UVs. Only the hand pass (same projection test as the item
// shader), 64x64 textures and head/hat-net UVs are touched; every other draw using this
// shader is exactly vanilla. See ResourcePack/AGENTS.md "Gun viewmodel core shader".
//
// The head model is emitted per layer as 24 head vertices then 24 hat vertices, contiguous,
// cube faces in the order DOWN, UP, WEST, NORTH, EAST, SOUTH (4 vertices each), so
// gl_VertexID % 48 identifies cube, face and corner. (Layer order is NOT stable on 1.21.11.)

#moj_import <minecraft:light.glsl>
#moj_import <minecraft:fog.glsl>
#moj_import <minecraft:dynamictransforms.glsl>
#moj_import <minecraft:projection.glsl>

in vec3 Position;
in vec4 Color;
in vec2 UV0;
in ivec2 UV1;
in ivec2 UV2;
in vec3 Normal;

uniform sampler2D Sampler0;
uniform sampler2D Sampler1;
uniform sampler2D Sampler2;

out float sphericalVertexDistance;
out float cylindricalVertexDistance;
#ifdef PER_FACE_LIGHTING
out vec4 vertexPerFaceColorBack;
out vec4 vertexPerFaceColorFront;
#else
out vec4 vertexColor;
#endif
out vec4 lightMapColor;
out vec4 overlayColor;
out vec2 texCoord0;
flat out int sgarmFace;   // -1 = vanilla vertex, else face (0..5) + 6 for the hat cube
out vec2 sgarmST;         // corner of the face rect: (0,0) = (x1,y1) ... (1,1) = (x2,y2)

void main() {
    gl_Position = ProjMat * ModelViewMat * vec4(Position, 1.0);

    sphericalVertexDistance = fog_spherical_distance(Position);
    cylindricalVertexDistance = fog_cylindrical_distance(Position);

    sgarmFace = -1;
    sgarmST = vec2(0.0);
    if (abs(ProjMat[3][2] + 0.10005) < 0.00001
        && textureSize(Sampler0, 0) == ivec2(64, 64)
        && UV0.y < 15.5 / 64.0) {
        int hat = (gl_VertexID % 48) / 24;
        // head net u <= 32, hat net u >= 32 (the two share u = 32 at their west/south edges)
        if (hat == 0 ? UV0.x < 0.5078125 : UV0.x > 0.4921875) {
            int k = gl_VertexID % 4;
            sgarmFace = (gl_VertexID % 24) / 4 + 6 * hat;
            // Polygon vertices: v0 = (x2,y1) v1 = (x1,y1) v2 = (x1,y2) v3 = (x2,y2)
            sgarmST = vec2((k == 0 || k == 3) ? 1.0 : 0.0, k >= 2 ? 1.0 : 0.0);
        }
    }

#ifdef PER_FACE_LIGHTING
    vec2 light = minecraft_compute_light(Light0_Direction, Light1_Direction, Normal);
    vertexPerFaceColorBack = minecraft_mix_light_separate(-light, Color);
    vertexPerFaceColorFront = minecraft_mix_light_separate(light, Color);
    if (sgarmFace >= 0) {
        // mirrored (back-facing) arm layers still have outward normals
        vertexPerFaceColorBack = vertexPerFaceColorFront;
    }
#elif defined(NO_CARDINAL_LIGHTING)
    vertexColor = Color;
#else
    vertexColor = minecraft_mix_light(Light0_Direction, Light1_Direction, Normal, Color);
#endif
#ifndef EMISSIVE
    lightMapColor = texelFetch(Sampler2, UV2 / 16, 0);
#endif
    overlayColor = texelFetch(Sampler1, UV1, 0);

    texCoord0 = UV0;
#ifdef APPLY_TEXTURE_MATRIX
    texCoord0 = (TextureMat * vec4(UV0, 0.0, 1.0)).xy;
#endif
}

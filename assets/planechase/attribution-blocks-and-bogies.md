# Attribution: Blocks and Bogies

The bogie models and textures under `models/item/bogie/`, `items/bogie/` and `textures/item/bogie/` are derived from
the **Blocks and Bogies** mod by **t__cup** and **weido's oddities**.

- Source: https://github.com/weido/Blocks-And-Bogies (Create add-on, `create_bb` assets)
- Copyright (c) 2026 t__cup, weido's oddities
- License: Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0),
  https://creativecommons.org/licenses/by-sa/4.0/ . These derived files are shared under the same license.

## Changes made

- The Blockbench / Blender OBJ meshes were converted by `tools/bogies/convert_bogies.py` (PlaneChase repository) into
  vanilla Minecraft item model JSON: each box of the mesh became one element (rotations in 22.5 degree steps kept),
  with UV, texture references and a `display.fixed` scale and translation so the model fits the vanilla coordinate limits.
- Models were moved so the wheel bottoms sit on the model origin plane (the rail contact point).
- Only static parts were converted: frames and wheels. Animated valve gear (rods, cranks, links, sliders) and parts that
  need Create's own textures (belts, shafts) were not converted or copied.
- Textures are unchanged copies: 32x32.png, 32x32_single.png, broad_piston.png, create_rods.png, extras.png, frame.png, frame2.png, frame4.png, piston.png, single.png, single_axle_body.png, small_frame.png, small_trailing_bogey_outer.png, trailing_bogey_base.png, wheel.png, xl_textures.png.
- Create assets (create:block/axis, create:block/bogey/belt, shaft models) are All Rights Reserved and are not included.

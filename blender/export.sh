#!/bin/zsh
# Rebuild the web assets for the homepage scene from blender/pavilion.blend.
#
#   blender/export.sh            # bake + export + optimise + posters
#   blender/export.sh --rebuild  # also rebuild pavilion.blend from the scripts first
#   blender/export.sh --quick    # fast low-quality bake (pipeline check only)
#
# Outputs (public/pavilion/): pavilion.glb, sky.webp, cameras.json,
# poster.webp, poster-portrait.webp. Intermediates live in blender/.build/.
set -euo pipefail
cd "${0:A:h}/.."
BLENDER=${BLENDER:-/Applications/Blender.app/Contents/MacOS/Blender}
OUT=public/pavilion
BUILD=blender/.build
BAKE_ARGS=()
for arg in "$@"; do
  case $arg in
    --rebuild) "$BLENDER" -b --factory-startup -P blender/build_scene.py ;;
    --quick) BAKE_ARGS+=(--quick) ;;
  esac
done

mkdir -p "$OUT" "$BUILD"
"$BLENDER" -b --factory-startup -P blender/bake_export.py -- "${BAKE_ARGS[@]}"

# Meshopt + quantisation, WebP textures. Keep the scene graph as exported: the
# page looks up cameras, anchors and materials by name, and anchors are empty
# nodes that pruning/flattening would drop.
npx -y @gltf-transform/cli@4 optimize "$BUILD/pavilion.raw.glb" "$OUT/pavilion.glb" \
  --compress meshopt --texture-compress webp --texture-size 4096 \
  --simplify false --join false --flatten false --instance false --palette false --prune false

cp "$BUILD/sky.webp" "$BUILD/cameras.json" "$OUT/"

# Posters: the Cycles hero renders, shown first and used as the fallback.
"$BLENDER" -b blender/pavilion.blend -P blender/render_stills.py -- "$BUILD" cam_hero cam_hero_portrait --webp
mv "$BUILD/hero.webp" "$OUT/poster.webp"
mv "$BUILD/hero_portrait.webp" "$OUT/poster-portrait.webp"
ls -la "$OUT"

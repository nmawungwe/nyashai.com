---
read_when:
  - Updating the pavilion homepage, its 3D scene, object links, or homepage copy
---

# Garden pavilion

The approved homepage introduction is exactly:

> Hi, I’m Nyasha.
>
> Building goveranAI and VhenekAI.

Keep the homepage quiet. Biography, descriptions, and article titles appear
inside the panels or on their existing pages. The AI-safety line was removed
from the homepage at Nyasha’s request; the About page and published writing
remain the sources of biographical detail.

## Implementation

The scene is a real 3D model: built procedurally in Blender, lit with Cycles,
and drawn in the browser with three.js. All lighting is baked, so the browser
draws unlit textures and vertex colours and the camera can truly move: it leans
with the pointer and flies to the laptop, the notebook and the books. The
interface uses actual HTML text and links; nothing is baked into the scene.

Sources live in `blender/`:

- `build_scene.py` and `pavlib/` build `pavilion.blend` from scratch
  (architecture, props, planting, cameras `cam_hero`, `cam_hero_portrait`,
  `cam_projects`, `cam_writing`, `cam_reviews`, and the label anchors).
- `bake_export.py` and `bakelib/` bake the lighting (texture atlases for
  architecture, masonry, furniture and ground; per-leaf vertex colours for
  planting) and export a GLB.
- `export.sh` runs the lot and writes `public/pavilion/`: `pavilion.glb`
  (meshopt + WebP, about 4 MB), `sky.webp`, `cameras.json`, and the two posters
  `poster.webp` / `poster-portrait.webp`, which are Cycles renders of the hero
  cameras.

```bash
blender/export.sh --rebuild   # rebuild pavilion.blend, bake, export (about 10 min)
blender/export.sh             # re-bake and export an existing pavilion.blend
blender/export.sh --quick     # low-quality pipeline check
```

It needs Blender 5.x (`brew install --cask blender`; set `BLENDER` to override
the path) and `npx`. `pavilion.blend` and `blender/.build/` are not committed;
the scripts are the source. Planting is culled to the camera frustums, so moving
a camera means a `--rebuild`. Textures are display-referred (AgX is applied at
bake time), so the page uses no tone mapping.

The distant hills are a matte painting (`pavlib/matte.py`): the clean hill areas
of `garden-desktop-personal.webp` and `garden-mobile-personal.webp`, resampled
onto a curved card 80 m out and feathered into the baked sky.

On the page, `src/scripts/pavilion/` holds the scene: `index.ts` (wiring and
lifecycle), `scene.ts` (loading, materials, breeze shader), `rig.ts` (camera
poses, flights, framing) and `labels.ts` (HTML labels projected from the 3D
anchors each frame). `pavilion-panels.ts` owns the dialogs. three.js is the one
runtime dependency and loads as a separate chunk after first paint.

The poster `<img>` is the first paint and the fallback: without WebGL, on
context loss or if loading fails, it stays. The camera's projection matches the
poster's `object-fit: cover` framing, so the hand-over is seamless. Landscape
viewports use `cam_hero` and align right to keep the reading bench; portrait and
square viewports use `cam_hero_portrait`.

Native `<dialog>` panels provide focus trapping, Escape dismissal, and return
focus to the triggering link. The visible links retain real destinations for
JavaScript-free use and opening in another tab. The mobile menu uses native
`<details>`. `/simple/` is an image-free alternative with the same content.

Project descriptions come from `src/data/projects.ts`. Writing/reviews come
from `src/content/`, sorted by date, excluding drafts, at build time. Publishing
new Markdown and rebuilding updates both the panels and Simple view.

## Motion

The poster settles in once over 1.2 seconds, with a short stagger for the
greeting. The 3D scene fades in over the identical poster once its first frame
is drawn. The pointer leans the camera by a few centimetres; a slow idle drift
keeps the depth visible when the pointer rests and on touch screens, where it is
stronger. Leaves and grasses sway in a vertex-shader breeze. Tune these with the
constants at the top of `rig.ts` and `scene.ts`.

Choosing a destination flies the camera to that object along a slight arc over
1.6 seconds while the greeting and labels fade; the panel opens on arrival. The
close-up is framed in the clear area beside the panel, or above it on phones,
where the panel is a bottom sheet (62% of the height; keep `panelHeight` in
`index.ts` and the rule in `pavilion.css` in step). Closing flies back. Behind
an open panel the scene stops drawing once the camera arrives, and it pauses in
a hidden tab.

Panels enter over 420ms and exit over 200ms, with a matching backdrop fade.
`pavilion-panels.ts` waits for the exit before closing the native dialog,
keeping its focus trap intact. Close, Escape, and backdrop dismissal share this
path; repeated close requests are ignored while an exit is pending. A
reduced-motion preference change or a hidden tab finishes pending exits
immediately. See the
[native dialog cancel event](https://developer.mozilla.org/en-US/docs/Web/API/HTMLDialogElement/cancel_event).

Reduced motion keeps the 3D scene but holds it still: no entrance, pointer lean,
idle drift, breeze or flights (the camera cuts to the destination), and no hover
lift or panel/backdrop animations. No-JavaScript links and native mobile
navigation remain available.

## Artwork provenance and prompt

The 3D scene was modelled after this artwork, which is no longer shown on the
homepage itself. It remains the source of the matte-painted hills and of the
reading pages' masthead. It was created with the built-in imagegen tool from
the user-approved Garden Pavilion mockups. Original generated files remain in the chat's generated-image storage.
The selected artwork is persisted in this repository:

- `src/assets/pavilion/garden-desktop-personal.webp` — 1672 × 941
- `src/assets/pavilion/garden-mobile-personal.webp` — 891 × 1765

Both were encoded as WebP at quality 94, then responsive derivatives are
generated by Astro. The original clean-background edit prompt was used for each approved
desktop/mobile reference:

> Use case: precise-object-edit / text removal. This is the approved Garden
> Pavilion website mockup. Create its CLEAN BACKGROUND ARTWORK for implementing
> the website with real HTML text. Remove ALL overlaid website text, lettering,
> labels, dots, leader lines, navigation, header brand, hamburger menu, greeting,
> subtitle, About link and simple-view link. For mobile also remove the pale
> bottom navigation strip and extend the garden scene naturally to the bottom
> edge. Seamlessly restore the natural sky, pavilion or garden that was beneath
> every removed UI element. Keep the scene composition, exact camera,
> proportions, aspect ratio, geometry, tree, pavilion, sunlit slatted roof,
> rammed-earth wall, worktable/laptop, books and notebook, plants, mountains and
> lighting EXACTLY as shown. It must be the same image without the interface.
> Do not redesign, move objects, change lighting, add people, add or alter
> plants, zoom or reframe. No text, logo, watermark, labels or UI. Preserve the
> pale sky and natural negative space where the greeting was. Final image is a
> high-quality photorealistic pre-rendered 3D scene background for the approved site.

Instrument Serif and DM Sans are self-hosted in `public/fonts/`, with their
respective SIL Open Font Licenses alongside them.

## Personal details and project previews (17 October 2026)

The current `-personal` scene variants were edited with the built-in imagegen
skill from the original scene and real public website screenshots. The laptop
faces the visitor with goveranAI on screen; the tablet shows VhenekAI. A cream
reading copy of *The Adolescence of Technology* by Dario Amodei sits on the
bench. It represents the published essay review, not a claimed book edition.
The site currently has no published book reviews, so other spines stay unlabelled.

Final prompt, shared by both compositions:

> Preserve the exact camera, architecture, composition, tree, vegetation, sky,
> colours, lighting, framing and aspect ratio. Change only the personal work
> objects: rotate the existing laptop in place so its screen faces the viewer,
> showing the real cream-and-green goveranAI website screenshot with realistic
> perspective, bezel and keyboard. The existing tablet shows the real VhenekAI
> landing page screenshot. Beside the books place a slender cream printed essay
> reading copy titled “The Adolescence of Technology”, “Dario Amodei” beneath,
> and small “ESSAY” above. Other book spines stay plain. These are quiet details
> physically in the scene; no floating headings, navigation, reframing or zoom.
> Portrait: put the reading copy on the visible right bench behind the table.
> Landscape: preserve existing object positions for the navigation hotspots.

Generated sources: `exec-a1d2b645-8697-4ef9-a413-db35991b12fe.png` (desktop),
`exec-1c581ca8-c6e4-4611-85d6-c01c83e33a31.png` (portrait) in this chat’s
generated-image directory. Original unpersonalised assets remain available.

Project previews are unaltered viewport captures of
https://www.goveranai.com/en and https://vhenekai.org/ taken on 17 October 2026,
excluding browser chrome/scrollbars, encoded to WebP. They are public website
previews, not screenshots of a private application or invented product UI.
The generated scene uses those captures as references; panel previews use the
actual captures. See `src/data/projects.ts` and `ProjectPreview.astro`.
Use a new capture when refreshing a preview; preserve the source URL and date.

The compact object labels retain at least 44px overall interactive height,
with a warm translucent surface and matching hover/keyboard focus feedback.
The panel close control stays visible as longer project previews scroll.

## Reading pages

`reading.css` gives About, Projects, Writing, Reviews and articles a shared
paper palette, spacious serif headings and a panoramic garden masthead. The
masthead is decorative. Simple view stays image-free. Navigation calls the blog
“Writing”, matching the homepage, and includes Projects. Existing article and
biographical content is preserved.

Reading pages default to warm paper even on a dark OS, connecting them visually
to the homepage. An explicit light/dark choice still persists. Dark reading mode
uses green-black ink tones and a subdued masthead. The homepage stays light.

Native CSS cross-document view transitions crossfade over 220ms on supporting
browsers. Ordinary links and fresh document loads are retained; there is no
client router or extra library. Reduced motion disables document transitions.
Unsupported browsers use ordinary page navigation. See
[MDN @view-transition](https://developer.mozilla.org/en-US/docs/Web/CSS/@view-transition).

## Verification for this refinement

Production build: eight static routes. Browser checks covered the homepage at
320, 393, 768, 1024, 1366 and 1920px widths, all content routes at 320px,
project preview loading, panel dismissal/focus, a reachable close button after
scrolling, and the saved dark-mode choice across navigation. No horizontal
overflow or browser errors were observed. All built local links/assets resolve;
Simple view emits no images. Reduced-motion guards cover the native page fade,
label feedback and the existing scene/panel effects.

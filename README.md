# nyashai.com

Personal site of Nyasha Mawungwe — built with [Astro](https://astro.build).
Static Astro site with a garden-pavilion homepage, a short introduction,
and object links to projects, writing, and reviews. The homepage uses optimized
rendered artwork with subtle pointer parallax; other pages retain the warm
"Sand & Terracotta" theme and automatic light/dark.

## Run it

```bash
npm install      # one time
npm run dev      # local dev server at http://localhost:4321
npm run build    # production build into dist/
npm run preview  # preview the production build locally
```

## Writing new content

Each entry is one Markdown file — no HTML, no code. Lists, dates and pages
generate automatically.

### A blog post

Create `src/content/blog/my-post.md`:

```markdown
---
title: "My post title"
date: 2026-06-21
description: "One-line summary shown in the list."
tags: ["optional", "tags"]
draft: false        # set true to hide it
---

Write your post in Markdown here.
```

### A review

Create `src/content/reviews/the-thing.md`:

```markdown
---
title: "The Pragmatic Programmer"
kind: book          # book | paper | blog | article
author: "Hunt & Thomas"
rating: 5           # optional, 1–5
date: 2026-06-21
link: "https://..."  # optional link to the original
summary: "One-line take shown in the list."
draft: false
---

Your review in Markdown here.
```

## Editing the basics

- **Name, tagline, social links:** `src/site.ts`
- **Home intro:** `src/pages/index.astro`
- **Projects:** `src/data/projects.ts` (shared by the homepage panel, Projects, and Simple view)
- **Homepage appearance and interaction:** `src/styles/pavilion.css`, `src/scripts/pavilion.ts`
- **Scene artwork:** `src/assets/pavilion/`
- **Colors & fonts:** `src/styles/global.css` (CSS variables at the top)
- **Profile photo:** replace `src/assets/profile.jpg`
- **Domain (for canonical URLs):** `astro.config.mjs`

## Garden homepage

Projects, Writing, and Reviews open native dialog panels. The latest three
published posts/reviews are generated from Markdown at build time; drafts stay
hidden. Without JavaScript, those links open their normal pages. `/simple/`
provides the content without the scene. Mobile has a portrait composition,
a native navigation menu, and larger links along the bottom.

Parallax runs only in response to a mouse pointer on desktop, stops when idle,
and respects reduced-motion preferences. Fonts are self-hosted and the scene
uses responsive WebP images; no third-party scripts or runtime requests are needed.
See [design and artwork notes](docs/pavilion.md) for the approved copy, image
provenance, and how object positions stay aligned.

## Deploy

Production is hosted on Vercel at `https://nyashai.com`, connected to the
`nmawungwe/nyashai.com` GitHub repository. Pushing `main` triggers a production
deployment. The build command is `npm run build`, with output in `dist/`.

Before pushing, verify the production build and the desktop/mobile interactions.
After pushing, check the commit's Vercel status and verify the live domain.

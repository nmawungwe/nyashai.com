# nyashai.com

Personal site of Nyasha Mawungwe — built with [Astro](https://astro.build).
Static, fast (ships ~zero JavaScript), warm "Sand & Terracotta" theme with
automatic light/dark.

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
- **Home intro & projects:** `src/pages/index.astro`
- **Colors & fonts:** `src/styles/global.css` (CSS variables at the top)
- **Profile photo:** replace `public/profile.jpg`
- **Domain (for canonical URLs):** `astro.config.mjs`

## Deploy

This is a static site, so any static host works. Easiest options:

- **Netlify / Cloudflare Pages / Vercel:** connect the repo, set build command
  `npm run build` and publish directory `dist`.
- **GitHub Pages:** build and push the `dist/` folder, or use the Astro GitHub
  Pages action.

import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

// Reviews: things I've read (books, papers, blog posts, articles) + my take.
const reviews = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/reviews' }),
  schema: z.object({
    title: z.string(),
    // What kind of thing this is a review of.
    kind: z.enum(['book', 'paper', 'blog', 'article']),
    author: z.string().optional(),
    // Optional 1–5 star rating; omit if you'd rather not rate.
    rating: z.number().min(1).max(5).optional(),
    date: z.coerce.date(),
    // Link to the original work, if it lives online.
    link: z.string().url().optional(),
    // One-line summary shown in the list view.
    summary: z.string(),
    draft: z.boolean().default(false),
  }),
});

// Blog: my own writing and thoughts.
const blog = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/blog' }),
  schema: z.object({
    title: z.string(),
    date: z.coerce.date(),
    description: z.string(),
    tags: z.array(z.string()).default([]),
    draft: z.boolean().default(false),
  }),
});

export const collections = { reviews, blog };

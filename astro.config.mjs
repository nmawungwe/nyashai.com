// @ts-check
import { defineConfig } from 'astro/config';

// Update `site` to your final domain so canonical URLs / sitemaps are correct.
export default defineConfig({
  site: 'https://nyashai.com',
  build: {
    inlineStylesheets: 'always',
  },
});

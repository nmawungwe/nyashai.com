import { getCollection } from 'astro:content';

const published = <T extends { data: { draft: boolean; date: Date } }>(items: T[]) =>
  items.filter(({ data }) => !data.draft)
    .sort((a, b) => b.data.date.valueOf() - a.data.date.valueOf())
    .slice(0, 3);

export async function getHomeContent() {
  const [posts, reviews] = await Promise.all([
    getCollection('blog'),
    getCollection('reviews'),
  ]);
  return { posts: published(posts), reviews: published(reviews) };
}

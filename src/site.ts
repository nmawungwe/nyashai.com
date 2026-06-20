// Single source of truth for site-wide identity + links.
// Edit these and they update everywhere (nav, footer, meta tags).
export const site = {
  name: 'Nyasha Mawungwe',
  tagline: 'Developer, Writer, Lifelong Learner',
  description:
    'Personal site of Nyasha Mawungwe — writing, reviews of books, papers and blogs, and notes on technology and learning.',
  socials: [
    { label: 'GitHub', href: 'https://github.com/nmawungwe' },
    { label: 'Twitter', href: 'https://twitter.com/nyasha_mawungwe' },
    { label: 'Email', href: 'mailto:nmawungwe@gmail.com' },
  ],
} as const;

export const nav = [
  { label: 'Home', href: '/' },
  { label: 'About', href: '/about' },
  { label: 'Reviews', href: '/reviews' },
  { label: 'Blog', href: '/blog' },
] as const;

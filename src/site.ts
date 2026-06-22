// Single source of truth for site-wide identity + links.
// Edit these and they update everywhere (nav, footer, meta tags).
export const site = {
  name: 'Nyasha Mawungwe',
  tagline: 'AI/ML Builder · Data Analyst · Pursuing AI Safety',
  description:
    'Personal site of Nyasha Mawungwe: AI/ML builder and data analyst moving into AI safety. Writing, reviews, and notes on machine learning and learning in public.',
  socials: [
    { label: 'GitHub', href: 'https://github.com/nmawungwe' },
    { label: 'LinkedIn', href: 'https://linkedin.com/in/nyasha22' },
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

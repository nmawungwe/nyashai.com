// Your background, in one place. Add/edit entries here and the About page
// updates automatically. Everything except `title` fields is optional-friendly —
// leave a list empty ([]) and its section won't render.

// A short bio shown at the top of the About page (supports a few sentences).
export const bio = [
  "I'm a developer and writer focused on technology, finance, and personal growth. I enjoy building practical tools, learning in public, and turning what I read into clear notes.",
  'Outside of work I read widely — papers, books, and blogs — and write up what sticks. (Edit this bio in src/data/cv.ts.)',
];

export interface ExperienceEntry {
  role: string;
  org: string;
  // e.g. "2023" or "2023 – Present"
  period: string;
  location?: string;
  // Optional bullet points describing what you did / achieved.
  highlights?: string[];
}

export const experience: ExperienceEntry[] = [
  {
    role: 'Your Role',
    org: 'Company / Organization',
    period: '2023 – Present',
    location: 'City, Country',
    highlights: [
      'A notable thing you built or achieved here.',
      'Another measurable result or responsibility.',
    ],
  },
  {
    role: 'Previous Role',
    org: 'Earlier Company',
    period: '2021 – 2023',
    highlights: ['What you owned and the impact you had.'],
  },
];

export interface EducationEntry {
  qualification: string;
  institution: string;
  period: string;
  detail?: string;
}

export const education: EducationEntry[] = [
  {
    qualification: 'Your Degree (e.g. BSc Computer Science)',
    institution: 'University Name',
    period: '2017 – 2021',
    detail: 'Honors, focus area, or a notable detail (optional).',
  },
];

export interface Certification {
  name: string;
  issuer: string;
  year: string;
  // Optional link to the credential / verification page.
  link?: string;
}

export const certifications: Certification[] = [
  {
    name: 'Notable Certification Name',
    issuer: 'Issuing Body',
    year: '2024',
    link: 'https://example.com/verify',
  },
  {
    name: 'Another Certification',
    issuer: 'Issuing Body',
    year: '2023',
  },
];

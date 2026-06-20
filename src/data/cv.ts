// Your background, in one place. Add/edit entries here and the About page
// updates automatically. Leave any list empty ([]) and its section won't render.

// A short bio shown at the top of the About page.
export const bio = [
  "I'm a data analyst with a chemical-engineering foundation and a self-taught grounding in machine learning and deep learning. Right now I'm helping build production AI products while moving fully into AI safety — to me, one of the most consequential problems of the coming decades.",
  'I pair analytical rigour with hands-on ML and an entrepreneurial track record of shipping technology that serves real communities. Based in Johannesburg, South Africa.',
];

// A few core skills, shown as chips under the bio.
export const skills: string[] = [
  'Python',
  'SQL',
  'Deep Learning',
  'Neural Networks',
  'TensorFlow',
  'CNNs',
  'Risk Modelling',
  'Data Analysis',
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
    role: 'Research & Development Specialist',
    org: 'VhenekAI',
    period: 'Jan 2026 – Present',
    highlights: [
      'Helping build an offline-first platform that delivers expert-level STEM education through on-device AI to underserved African communities.',
      'Prototyping privacy-preserving, curriculum-aligned tools (offline AI chat, adaptive learner profiling) that run on low-end devices with no internet — learner data stays on-device and the tool supports teachers rather than replacing them.',
    ],
  },
  {
    role: 'Member of Technical Staff · Builder',
    org: 'goveranAI — Zimbabwe Fresh Produce Marketplace',
    period: 'Jan 2026 – Present',
    location: 'Harare, Zimbabwe',
    highlights: [
      'Helping build a WhatsApp-based marketplace that uses AI to connect Zimbabwean farmers directly with buyers — listing, matching, and trust/safety workflows, no app required.',
      'Built Market Radar, an AI tool giving farmers early warning of produce price moves; every alert cites its sources and a counter-signal, prioritising calibration over overconfident predictions.',
    ],
  },
  {
    role: 'Junior Analyst',
    org: 'Elenjical Solutions',
    period: '2025 – Present',
    highlights: [
      'Provide production support for the Murex trading platform — resolving ~5 daily trade-booking and lifecycle issues at 99.9% uptime.',
      'Automate P&L and risk data feeds in Python/SQL, cutting manual reconciliation time 10–15%.',
    ],
  },
  {
    role: 'Founder & CEO',
    org: 'Why Nut',
    period: '2017 – 2022',
    highlights: [
      'Founded a healthy-snack business serving 30,000 students; led a 3-person team to ~R20,000/month revenue, 5 campus outlets, and national media coverage.',
    ],
  },
  {
    role: 'Process Engineer Intern',
    org: 'Tetra Pak',
    period: '2017 – 2018',
    highlights: [
      'Helped optimise a 500k L/month dairy processing line, contributing to an 8% reduction in line downtime through data-driven scheduling.',
    ],
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
    qualification: 'MSc, Chemical Engineering',
    institution: 'University of Cape Town',
    period: '2019 – 2023',
    detail:
      'Thesis: ultrasonic spray fabrication of catalyst-coated membranes for PEM water electrolysers (30% reduction in catalyst loading).',
  },
  {
    qualification: 'BSc (Hons), Chemical Engineering',
    institution: 'University of Cape Town',
    period: '2015 – 2018',
    detail: 'Final project: techno-economic analysis of a 10 t/day biobutanol facility.',
  },
];

export interface Certification {
  name: string;
  issuer: string;
  year?: string;
  // Optional link to the credential / verification page.
  link?: string;
}

export const certifications: Certification[] = [
  { name: 'Deep Learning Specialization', issuer: 'DeepLearning.AI' },
  { name: 'Introduction to TensorFlow for AI, ML & Deep Learning', issuer: 'DeepLearning.AI' },
  { name: 'ACI Dealing Certificate', issuer: 'ACI Financial Markets Association', year: '2025' },
];

import goveranPreview from '../assets/projects/goveranai.webp';
import vhenekPreview from '../assets/projects/vhenekai.webp';

export const projects = [
  {
    title: 'goveranAI',
    description:
      'A WhatsApp-based AI marketplace connecting Zimbabwean farmers with buyers, plus Market Radar for early price signals.',
    url: 'https://www.goveranai.com/en',
    category: 'Agriculture',
    host: 'goveranai.com',
    preview: goveranPreview,
    previewAlt: 'goveranAI’s public website, showing its agricultural marketplace and WhatsApp channel preview.',
  },
  {
    title: 'VhenekAI',
    description:
      'Offline-first, on-device AI bringing expert-level STEM education to underserved African communities.',
    url: 'https://vhenekai.org/',
    category: 'Education',
    host: 'vhenekai.org',
    preview: vhenekPreview,
    previewAlt: 'VhenekAI’s public website introducing offline STEM education and its beta programme.',
  },
] as const;

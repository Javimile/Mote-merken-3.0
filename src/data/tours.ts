
export type Tour = {
  id: string;
  apiId: number;
  destinationId: string;
  slug: string;
  name: string;
  location: string;
  region: string;
  image: string;
  eyebrow: string;
  summary: string;
  description: string;
  experience: 'Culture' | 'Adventure' | 'Nature' | 'City';
  format: 'Private' | 'Tailor-made';
  highlights: string[];
  latitude: number;
  longitude: number;
};

// Datos visuales del frontend asociados a los IDs reales de Django.
export const tours: Tour[] = [

   
  
  {
    id: 'TOU-0000',
    apiId: 1,
    destinationId: '',
    slug: 'daddy',
    name: 'daddy',
    location: 'Chile',
    region: 'Chile',
    image: '/assets/baltinache.jpg',
    eyebrow: 'Tour disponible',
    summary: 'Consulta los detalles de esta experiencia.',
    description: 'Consulta los detalles de esta experiencia con nuestro equipo.',
    experience: 'Nature',
    format: 'Private',
    latitude: -33.4489,
    longitude: -70.6693,
    highlights: ['Experiencia disponible'],
  },

  {
    id: 'TOU-0001',
    apiId: 6,
    destinationId: 'DES-0001',
    slug: 'atacama-baltinache',
    name: 'Baltinache & Atacama',
    location: 'San Pedro de Atacama',
    region: 'Atacama Desert',
    image: '/assets/baltinache.jpg',
    eyebrow: 'Northern Chile',
    summary: 'Salt lagoons, desert light and otherworldly landscapes in the driest desert on Earth.',
    description: 'A private Atacama experience shaped around the landscapes and rhythms of northern Chile. The final route, schedule and services will be supplied by the booking backend once confirmed with the client.',
    experience: 'Nature',
    format: 'Tailor-made',
    latitude: -22.9112,
    longitude: -68.2011,
    highlights: ['Baltinache lagoons', 'Atacama landscapes', 'Private travel style'],
  },
  {
    id: 'TOU-0002',
    apiId: 7,
    destinationId: 'DES-0002',
    slug: 'rapa-nui',
    name: 'Rapa Nui',
    location: 'Easter Island',
    region: 'Rapa Nui',
    image: '/assets/rapa-nui.jpg',
    eyebrow: 'Pacific Chile',
    summary: 'Ancestral culture, volcanic scenery and the extraordinary heritage of Rapa Nui.',
    description: 'Discover Rapa Nui through a carefully curated private journey. Detailed itinerary, availability and confirmed rates will come from Django when the reservation module is connected.',
    experience: 'Culture',
    format: 'Private',
    latitude: -27.1127,
    longitude: -109.3497,
    highlights: ['Rapa Nui heritage', 'Volcanic landscapes', 'Local cultural context'],
  },
  {
    id: 'TOU-0003',
    apiId: 8,
    destinationId: 'DES-0003',
    slug: 'pucon',
    name: 'Pucón',
    location: 'Pucón',
    region: 'Araucanía',
    image: '/assets/pucon.jpg',
    eyebrow: 'Southern Chile',
    summary: 'Volcanoes, forests and outdoor experiences surrounded by the landscapes of Araucanía.',
    description: 'A flexible southern Chile experience centered on Pucón and its natural setting. Activities, operational times and availability remain ready to be populated from the future API.',
    experience: 'Adventure',
    format: 'Tailor-made',
    latitude: -39.282,
    longitude: -71.9543,
    highlights: ['Volcanic scenery', 'Outdoor experiences', 'Southern forests'],
  },
  {
    id: 'TOU-0004',
    apiId: 9,
    destinationId: 'DES-0004',
    slug: 'santiago',
    name: 'Santiago',
    location: 'Santiago',
    region: 'Metropolitan Region',
    image: '/assets/santiago.jpg',
    eyebrow: 'Central Chile',
    summary: 'Architecture, gastronomy, neighborhoods and the Andes from Chile’s capital.',
    description: 'A private introduction to Santiago designed around culture, city life and the Andes. Confirmed schedules and bookable services will later be managed from Django and MongoDB.',
    experience: 'City',
    format: 'Private',
    latitude: -33.4489,
    longitude: -70.6693,
    highlights: ['Urban culture', 'Local gastronomy', 'Andean setting'],
  },

    {
    id: 'TOU-0010',
    apiId: 10,
    destinationId: 'DES-0005',
    slug: 'valparaiso-cultural',
    name: 'Valparaíso Cultural',
    location: 'Valparaíso',
    region: 'Región de Valparaíso',
    image: '/assets/santiago.jpg',
    eyebrow: 'Central Chile',
    summary: 'Discover the colorful hills, historic architecture and coastal character of Valparaíso.',
    description: 'A cultural journey through Valparaíso, exploring its historic neighborhoods, architecture and Pacific coastal atmosphere. The final itinerary and services will be confirmed before booking.',
    experience: 'Culture',
    format: 'Private',
    latitude: -33.0472,
    longitude: -71.6127,
    highlights: [
      'Historic neighborhoods',
      'Colorful hillside architecture',
      'Pacific coastal views',
    ],
  },
  {
    id: 'TOU-0011',
    apiId: 11,
    destinationId: 'DES-0006',
    slug: 'torres-del-paine',
    name: 'Torres del Paine',
    location: 'Torres del Paine',
    region: 'Patagonia',
    image: '/assets/pucon.jpg',
    eyebrow: 'Southern Chile',
    summary: 'Explore the dramatic mountains, lakes and wild landscapes of Chilean Patagonia.',
    description: 'A nature-focused journey through the landscapes of Torres del Paine. The final route, activities, schedule and included services will be confirmed before booking.',
    experience: 'Adventure',
    format: 'Tailor-made',
    latitude: -50.9423,
    longitude: -73.4068,
    highlights: [
      'Patagonian mountain scenery',
      'Lakes and glaciers',
      'Wild landscapes',
    ],
  },
  {
    id: 'TOU-0012',
    apiId: 12,
    destinationId: 'DES-0007',
    slug: 'valle-del-elqui',
    name: 'Valle del Elqui',
    location: 'Valle del Elqui',
    region: 'Región de Coquimbo',
    image: '/assets/baltinache.jpg',
    eyebrow: 'Northern Chile',
    summary: 'Discover mountain valleys, clear skies and the distinctive landscapes of the Elqui Valley.',
    description: 'A flexible journey through the Elqui Valley, known for its mountain scenery and clear skies. The final itinerary, activities and services will be confirmed before booking.',
    experience: 'Nature',
    format: 'Tailor-made',
    latitude: -30.0277,
    longitude: -70.7081,
    highlights: [
      'Mountain valley landscapes',
      'Clear night skies',
      'Local culture',
    ],
  },
];

export const getTourBySlug = (slug: string) =>
  tours.find((tour) => tour.slug === slug);

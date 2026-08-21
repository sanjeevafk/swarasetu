export interface PHC {
  id: string;
  name: string;
  distance: number; // in km
  hours: string;
  coordinates: [number, number]; // lat, lng
  doctorAvailable: boolean;
}

export const mockPHCs: PHC[] = [
  {
    id: 'phc-1',
    name: 'Belsand Primary Health Center',
    distance: 4.2,
    hours: '24/7',
    coordinates: [26.4468, 85.3402],
    doctorAvailable: true,
  },
  {
    id: 'phc-2',
    name: 'Runnisaidpur Block Hospital',
    distance: 12.8,
    hours: '9 AM - 5 PM',
    coordinates: [26.3768, 85.3852],
    doctorAvailable: false,
  },
  {
    id: 'phc-3',
    name: 'Dumra Community Health Centre',
    distance: 21.5,
    hours: '24/7',
    coordinates: [26.5868, 85.3902],
    doctorAvailable: true,
  },
  {
    id: 'phc-4',
    name: 'Pupri Referral Hospital',
    distance: 28.1,
    hours: '24/7',
    coordinates: [26.5068, 85.6402],
    doctorAvailable: true,
  },
  {
    id: 'phc-5',
    name: 'Sursand Health Sub-Center',
    distance: 18.3,
    hours: '9 AM - 2 PM',
    coordinates: [26.6168, 85.5402],
    doctorAvailable: false,
  }
];

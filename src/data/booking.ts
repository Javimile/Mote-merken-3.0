export type BookingSeed = {
  id: string;
  tourId: string;
  tourSlug: string;
  scheduleIds: string[];
  schedules: { id: string; label: string }[];
  blockedDayNumbers: number[];
  maxTravellers: number;
  approvalBusinessDays: number;
  paymentProvider: 'Webpay';
};

// Frontend-only booking seed. Django will later return live availability,
// schedules, approval deadlines and payment session data using these same IDs.
export const bookingSeeds: BookingSeed[] = [


    {
    id: 'BKGCFG-DADDY',
    tourId: 'TOU-0001',
    tourSlug: 'daddy',
    scheduleIds: ['HOR-DADDY-01', 'HOR-DADDY-02'],
    schedules: [
      { id: 'HOR-DADDY-01', label: '08:00 AM' },
      { id: 'HOR-DADDY-02', label: '02:30 PM' },
    ],
    blockedDayNumbers: [],
    maxTravellers: 8,
    approvalBusinessDays: 5,
    paymentProvider: 'Webpay',
  },
  {
    id: 'BKGCFG-0001',
    tourId: 'TOU-0001',
    tourSlug: 'atacama-baltinache',
    scheduleIds: ['HOR-0001', 'HOR-0002'],
    schedules: [
      { id: 'HOR-0001', label: '08:00 AM' },
      { id: 'HOR-0002', label: '02:30 PM' },
    ],
    blockedDayNumbers: [5, 9, 14, 21, 27],
    maxTravellers: 8,
    approvalBusinessDays: 5,
    paymentProvider: 'Webpay',
  },
  {
    id: 'BKGCFG-0002',
    tourId: 'TOU-0002',
    tourSlug: 'rapa-nui',
    scheduleIds: ['HOR-0003', 'HOR-0004'],
    schedules: [
      { id: 'HOR-0003', label: '09:00 AM' },
      { id: 'HOR-0004', label: '01:30 PM' },
    ],
    blockedDayNumbers: [4, 10, 16, 22, 28],
    maxTravellers: 6,
    approvalBusinessDays: 5,
    paymentProvider: 'Webpay',
  },
  {
    id: 'BKGCFG-0003',
    tourId: 'TOU-0003',
    tourSlug: 'pucon',
    scheduleIds: ['HOR-0005', 'HOR-0006'],
    schedules: [
      { id: 'HOR-0005', label: '07:30 AM' },
      { id: 'HOR-0006', label: '11:00 AM' },
    ],
    blockedDayNumbers: [6, 12, 18, 24, 30],
    maxTravellers: 8,
    approvalBusinessDays: 5,
    paymentProvider: 'Webpay',
  },
  {
    id: 'BKGCFG-0004',
    tourId: 'TOU-0004',
    tourSlug: 'santiago',
    scheduleIds: ['HOR-0007', 'HOR-0008'],
    schedules: [
      { id: 'HOR-0007', label: '10:00 AM' },
      { id: 'HOR-0008', label: '03:00 PM' },
    ],
    blockedDayNumbers: [3, 11, 17, 23, 29],
    maxTravellers: 10,
    approvalBusinessDays: 5,
    paymentProvider: 'Webpay',
  },
];

export const getBookingSeed = (slug: string) => bookingSeeds.find((item) => item.tourSlug === slug);

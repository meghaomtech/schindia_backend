import type {
  BillPayerBalance,
  Centre,
  Child,
  ChildEnrolment,
  OpeningTimes,
  Purchase,
  Role,
  Session,
  SessionSlot,
  Teacher,
} from './types';
import { paletteFor } from './colors';
import { buildPermissionsForPreset } from './permissions';

const fullWeekOpen: OpeningTimes = {
  mon: { open: true, opensAt: '07:30', closesAt: '18:00' },
  tue: { open: true, opensAt: '07:30', closesAt: '18:00' },
  wed: { open: true, opensAt: '07:30', closesAt: '18:00' },
  thu: { open: true, opensAt: '07:30', closesAt: '18:00' },
  fri: { open: true, opensAt: '07:30', closesAt: '17:30' },
  sat: { open: false, opensAt: '', closesAt: '' },
  sun: { open: false, opensAt: '', closesAt: '' },
};

export const seedTeachers: Teacher[] = [
  { id: 't1', name: 'Ms. Johnson' },
  { id: 't2', name: 'Mr. Patel' },
  { id: 't3', name: 'Ms. Williams' },
  { id: 't4', name: 'Mr. Ahmed' },
  { id: 't5', name: 'Ms. Garcia' },
];

export const seedCentres: Centre[] = [
  {
    id: 'c1',
    systemId: 'CTR-001',
    name: 'Sunshine Nursery',
    streetAddress: '12 Oak Lane',
    city: 'London',
    postcode: 'E1 4AB',
    vatNumber: 'GB123456789',
    phone: '020 7946 0101',
    email: 'sunshine@nursery.co.uk',
    managerName: 'Helen Brooks',
    rooms: [
      { id: 'r1', name: 'Babies' },
      { id: 'r2', name: 'Toddlers' },
      { id: 'r3', name: 'Pre-school' },
    ],
    closureDates: [],
    openingTimes: fullWeekOpen,
  },
  {
    id: 'c2',
    systemId: 'CTR-002',
    name: 'Little Stars',
    streetAddress: '4 Star Street',
    city: 'London',
    postcode: 'NW1 2BA',
    phone: '020 1111 2222',
    email: 'hello@littlestars.co.uk',
    managerName: 'Rajesh Kumar',
    rooms: [
      { id: 'r4', name: 'Babies' },
      { id: 'r5', name: 'Toddlers' },
    ],
    closureDates: [],
    openingTimes: fullWeekOpen,
  },
];

function withPalette(s: Omit<Session, 'colorBg' | 'colorText'>): Session {
  const p = paletteFor(s.name);
  return { ...s, colorBg: p.bg, colorText: p.text };
}

export const seedSessions: Session[] = [
  withPalette({
    id: 's1',
    centreId: 'c1',
    name: 'Puppies',
    childLimit: 8,
    ageFrom: 0,
    ageTo: 12,
    ageUnit: 'months',
    durationHours: 1,
    durationMinutes: 30,
  }),
  withPalette({
    id: 's2',
    centreId: 'c1',
    name: 'Bears',
    childLimit: 12,
    ageFrom: 1,
    ageTo: 2,
    ageUnit: 'years',
    durationHours: 1,
    durationMinutes: 30,
  }),
  withPalette({
    id: 's3',
    centreId: 'c1',
    name: 'Cubs',
    childLimit: 10,
    ageFrom: 2,
    ageTo: 3,
    ageUnit: 'years',
    durationHours: 2,
    durationMinutes: 0,
  }),
  withPalette({
    id: 's4',
    centreId: 'c2',
    name: 'Stars',
    childLimit: 8,
    ageFrom: 1,
    ageTo: 3,
    ageUnit: 'years',
    durationHours: 1,
    durationMinutes: 30,
  }),
];

export const seedSlots: SessionSlot[] = [
  {
    id: 'slot1',
    centreId: 'c1',
    roomId: 'r1',
    sessionId: 's1',
    day: 'mon',
    startTime: '09:00',
    bookingType: 'recurring',
    startDate: '2026-04-15',
    endDate: '2026-09-30',
    startingMonth: 1,
    startingWeek: 1,
    teacherIds: ['t1'],
    childIds: [],
    notes: '',
  },
  {
    id: 'slot2',
    centreId: 'c1',
    roomId: 'r2',
    sessionId: 's2',
    day: 'tue',
    startTime: '10:00',
    bookingType: 'recurring',
    startDate: '2026-04-15',
    endDate: '2026-09-30',
    startingMonth: 1,
    startingWeek: 1,
    teacherIds: ['t2', 't3'],
    childIds: [],
    notes: '',
  },
  {
    id: 'slot3',
    centreId: 'c1',
    roomId: 'r3',
    sessionId: 's3',
    day: 'wed',
    startTime: '11:00',
    bookingType: 'recurring',
    startDate: '2026-04-15',
    endDate: '2026-09-30',
    startingMonth: 1,
    startingWeek: 1,
    teacherIds: ['t1'],
    childIds: ['ch1'],
    notes: 'Bring a snack',
  },
  {
    id: 'slot4',
    centreId: 'c1',
    roomId: 'r3',
    sessionId: 's3',
    day: 'fri',
    startTime: '09:30',
    bookingType: 'recurring',
    startDate: '2026-04-15',
    endDate: '2026-09-30',
    startingMonth: 1,
    startingWeek: 1,
    teacherIds: ['t4'],
    childIds: [],
    notes: '',
  },
];

export const seedChildren: Child[] = [
  {
    id: 'ch1',
    systemId: 'CHD-00142',
    firstName: 'Olivia',
    middleName: 'Grace',
    lastName: 'Lawson',
    gender: 'Female',
    centreId: 'c1',
    sessionId: 's3',
    dateOfBirth: '2022-03-14',
    startDate: '2026-04-07',
    contacts: [
      {
        id: 'co1',
        name: 'Sarah Lawson',
        relation: 'Mother',
        phone: '07700 900 123',
        email: 'sarah.lawson@email.com',
        inviteAs: 'Parent',
        isMain: true,
        isBillPayer: true,
        isEmergency: true,
      },
      {
        id: 'co2',
        name: 'James Lawson',
        relation: 'Father',
        phone: '07700 900 456',
        email: 'james.lawson@email.com',
        inviteAs: 'Parent',
        isMain: false,
        isBillPayer: true,
        isEmergency: false,
      },
      {
        id: 'co3',
        name: 'Dorothy Lawson',
        relation: 'Grandmother',
        phone: '07700 900 789',
        email: '',
        inviteAs: "Don't invite",
        isMain: false,
        isBillPayer: false,
        isEmergency: true,
      },
    ],
  },
];

export const seedEnrolments: ChildEnrolment[] = [
  {
    id: 'enr1',
    childId: 'ch1',
    slotId: 'slot3',
    startDate: '2026-04-15',
    endDate: '2026-09-30',
  },
];

export const seedPurchases: Purchase[] = [
  {
    id: 'pur1',
    kind: 'Session',
    name: 'Cubs — May block',
    date: '2026-05-01',
    amount: 240.0,
    paid: true,
  },
  {
    id: 'pur2',
    kind: 'Consumable',
    name: 'Workbook set',
    date: '2026-04-22',
    amount: 18.5,
    paid: true,
  },
  {
    id: 'pur3',
    kind: 'Late fee',
    name: 'Late pickup — 19 May',
    date: '2026-05-19',
    amount: 12.0,
    paid: false,
  },
];

export const seedBillPayerBalances: BillPayerBalance[] = [
  {
    contactId: 'co1',
    balance: 0,
    lastNote: 'Last invoice paid 1 May 2026',
  },
  {
    contactId: 'co2',
    balance: 12.0,
    lastNote: 'Late fee unpaid — 19 May',
  },
];

export const seedRoles: Role[] = [
  {
    id: 'role_mgr_c1',
    centreId: 'c1',
    name: 'Manager',
    description: 'Full or near-full access to all features. Responsible for site configuration, staff management, and financial oversight.',
    permissions: buildPermissionsForPreset('Manager'),
    members: [
      { id: 'rm1', name: 'Helen Brooks', email: 'helen.brooks@sunshine.co.uk' },
    ],
  },
  {
    id: 'role_tch_c1',
    centreId: 'c1',
    name: 'Teacher',
    description: 'Day-to-day operational access. Can manage children, communications, and learning content. Limited financial and admin access.',
    permissions: buildPermissionsForPreset('Teacher'),
    members: [
      { id: 'rm2', name: 'Ms. Johnson', email: 'johnson@sunshine.co.uk' },
      { id: 'rm3', name: 'Mr. Patel', email: 'patel@sunshine.co.uk' },
    ],
  },
  {
    id: 'role_par_c1',
    centreId: 'c1',
    name: 'Parent',
    description: "Limited read-only access to their own child's information, invoices, and communications from the setting.",
    permissions: buildPermissionsForPreset('Parent'),
    members: [
      { id: 'rm4', name: 'Sarah Lawson', email: 'sarah.lawson@email.com' },
    ],
  },
  {
    id: 'role_mgr_c2',
    centreId: 'c2',
    name: 'Manager',
    description: 'Full or near-full access to all features. Responsible for site configuration, staff management, and financial oversight.',
    permissions: buildPermissionsForPreset('Manager'),
    members: [
      { id: 'rm5', name: 'Rajesh Kumar', email: 'rajesh@littlestars.co.uk' },
    ],
  },
  {
    id: 'role_tch_c2',
    centreId: 'c2',
    name: 'Teacher',
    description: 'Day-to-day operational access. Can manage children, communications, and learning content. Limited financial and admin access.',
    permissions: buildPermissionsForPreset('Teacher'),
    members: [],
  },
  {
    id: 'role_par_c2',
    centreId: 'c2',
    name: 'Parent',
    description: "Limited read-only access to their own child's information, invoices, and communications from the setting.",
    permissions: buildPermissionsForPreset('Parent'),
    members: [],
  },
];

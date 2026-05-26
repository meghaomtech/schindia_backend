export type ID = string;

export type Gender = 'Male' | 'Female' | 'Other' | 'Prefer not to say';

export type AgeUnit = 'months' | 'years';

export type DayKey = 'mon' | 'tue' | 'wed' | 'thu' | 'fri' | 'sat' | 'sun';

export interface OpeningTime {
  open: boolean;
  opensAt: string;
  closesAt: string;
}

export type OpeningTimes = Record<DayKey, OpeningTime>;

export interface Centre {
  id: ID;
  systemId: string;
  name: string;
  streetAddress: string;
  city: string;
  postcode: string;
  vatNumber?: string;
  phone: string;
  email: string;
  managerName: string;
  rooms: Room[];
  closureDates: string[];
  openingTimes: OpeningTimes;
}

export interface Room {
  id: ID;
  name: string;
}

export interface Session {
  id: ID;
  name: string;
  childLimit: number;
  ageFrom: number;
  ageTo: number;
  ageUnit: AgeUnit;
  durationHours: number;
  durationMinutes: number;
  colorBg: string;
  colorText: string;
}

export type BookingType = 'one-off' | 'recurring';

export interface SessionSlot {
  id: ID;
  centreId: ID;
  roomId: ID;
  sessionId: ID;
  day: DayKey;
  startTime: string;
  bookingType: BookingType;
  startDate: string;
  endDate?: string;
  startingMonth: number;
  startingWeek: number;
  teacherIds: ID[];
  childIds: ID[];
  notes?: string;
}

export interface Teacher {
  id: ID;
  name: string;
}

export type ContactInviteAs = "Don't invite" | 'Parent' | 'Guardian' | 'Carer';

export interface Contact {
  id: ID;
  name: string;
  relation: string;
  phone: string;
  email: string;
  inviteAs: ContactInviteAs;
  isMain: boolean;
  isBillPayer: boolean;
  isEmergency: boolean;
}

export interface Child {
  id: ID;
  systemId: string;
  firstName: string;
  middleName?: string;
  lastName: string;
  gender: Gender;
  centreId: ID;
  sessionId?: ID;
  dateOfBirth: string;
  startDate: string;
  siblingId?: ID;
  contacts: Contact[];
}

export interface ChildEnrolment {
  id: ID;
  childId: ID;
  slotId: ID;
  startDate: string;
  endDate: string;
}

export type PurchaseKind = 'Session' | 'Consumable' | 'Late fee';

export interface Purchase {
  id: ID;
  kind: PurchaseKind;
  name: string;
  date: string;
  amount: number;
  paid: boolean;
}

export interface BillPayerBalance {
  contactId: ID;
  balance: number;
  lastNote: string;
}

export type JourneyType = 'Milestone' | 'Observation';

export interface JourneyEntry {
  id: ID;
  childId: ID;
  type: JourneyType;
  text: string;
  date: string;
  staffName: string;
}

export interface ChildNote {
  id: ID;
  childId: ID;
  text: string;
  date: string;
  staffName: string;
}

export interface ValidationError {
  field: string;
  message: string;
}

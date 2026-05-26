import { describe, expect, it } from 'vitest';
import { progressForWeek, slotAppearsOnDate, weekDates } from '../recurrence';
import type { Centre, OpeningTimes, SessionSlot } from '../types';
import { fromISODate } from '../dates';

const fullWeekOpen: OpeningTimes = {
  mon: { open: true, opensAt: '08:00', closesAt: '18:00' },
  tue: { open: true, opensAt: '08:00', closesAt: '18:00' },
  wed: { open: true, opensAt: '08:00', closesAt: '18:00' },
  thu: { open: true, opensAt: '08:00', closesAt: '18:00' },
  fri: { open: true, opensAt: '08:00', closesAt: '18:00' },
  sat: { open: false, opensAt: '', closesAt: '' },
  sun: { open: false, opensAt: '', closesAt: '' },
};

const centre: Centre = {
  id: 'c1',
  systemId: 'CTR-001',
  name: 'Test',
  streetAddress: 'a',
  city: 'b',
  postcode: 'c',
  phone: 'd',
  email: 'e@f.gh',
  managerName: 'M',
  rooms: [],
  closureDates: ['2026-05-25'],
  openingTimes: fullWeekOpen,
};

const baseSlot: SessionSlot = {
  id: 'slot1',
  centreId: 'c1',
  roomId: 'r1',
  sessionId: 's1',
  day: 'mon',
  startTime: '09:00',
  bookingType: 'recurring',
  startDate: '2026-04-13', // Monday
  endDate: '2026-06-29',
  startingMonth: 1,
  startingWeek: 1,
  teacherIds: [],
  childIds: [],
};

describe('progressForWeek', () => {
  it('returns starting MW on the first week', () => {
    const p = progressForWeek(baseSlot, fromISODate('2026-04-13'));
    expect(p).toEqual({ month: 1, week: 1 });
  });

  it('advances by 1 week each week', () => {
    const p2 = progressForWeek(baseSlot, fromISODate('2026-04-20'));
    expect(p2).toEqual({ month: 1, week: 2 });
    const p3 = progressForWeek(baseSlot, fromISODate('2026-04-27'));
    expect(p3).toEqual({ month: 1, week: 3 });
    const p4 = progressForWeek(baseSlot, fromISODate('2026-05-04'));
    expect(p4).toEqual({ month: 1, week: 4 });
  });

  it('rolls Week 4 → Month +1 Week 1', () => {
    const p = progressForWeek(baseSlot, fromISODate('2026-05-11'));
    expect(p).toEqual({ month: 2, week: 1 });
  });

  it('returns starting MW for one-off bookings', () => {
    const oneOff = { ...baseSlot, bookingType: 'one-off' as const };
    const p = progressForWeek(oneOff, fromISODate('2026-12-01'));
    expect(p).toEqual({ month: 1, week: 1 });
  });
});

describe('slotAppearsOnDate', () => {
  it('renders on matching weekdays within range', () => {
    expect(slotAppearsOnDate(baseSlot, fromISODate('2026-04-13'), centre)).toBe(true);
    expect(slotAppearsOnDate(baseSlot, fromISODate('2026-04-20'), centre)).toBe(true);
  });

  it('does not render outside the date range', () => {
    expect(slotAppearsOnDate(baseSlot, fromISODate('2026-04-06'), centre)).toBe(false);
    expect(slotAppearsOnDate(baseSlot, fromISODate('2026-07-06'), centre)).toBe(false);
  });

  it('does not render on closure dates', () => {
    expect(slotAppearsOnDate(baseSlot, fromISODate('2026-05-25'), centre)).toBe(false);
  });

  it('does not render on closed days', () => {
    expect(slotAppearsOnDate(baseSlot, fromISODate('2026-04-18'), centre)).toBe(false); // Saturday
  });

  it('one-off appears only on its startDate', () => {
    const oneOff = {
      ...baseSlot,
      bookingType: 'one-off' as const,
      startDate: '2026-04-15',
    };
    expect(slotAppearsOnDate(oneOff, fromISODate('2026-04-15'), centre)).toBe(true);
    expect(slotAppearsOnDate(oneOff, fromISODate('2026-04-22'), centre)).toBe(false);
  });
});

describe('weekDates', () => {
  it('returns 7 dates starting Monday', () => {
    const dates = weekDates(fromISODate('2026-05-29')); // Friday
    expect(dates).toHaveLength(7);
    expect(dates[0]?.getDay()).toBe(1); // Monday
    expect(dates[6]?.getDay()).toBe(0); // Sunday
  });
});

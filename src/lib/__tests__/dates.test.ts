import { describe, expect, it } from 'vitest';
import {
  addDays,
  ageInMonths,
  ageString,
  dayKeyForDate,
  fromISODate,
  getCalendarMonth,
  isSameDay,
  minutesToTime,
  startOfWeek,
  timeToMinutes,
  toISODate,
} from '../dates';

describe('toISODate / fromISODate', () => {
  it('round trips a date', () => {
    const d = new Date(2026, 4, 25);
    expect(toISODate(d)).toBe('2026-05-25');
    expect(toISODate(fromISODate('2026-05-25'))).toBe('2026-05-25');
  });
});

describe('startOfWeek', () => {
  it('returns Monday for any weekday', () => {
    // 2026-05-25 is a Monday → expect itself
    const d = new Date(2026, 4, 25);
    expect(toISODate(startOfWeek(d))).toBe('2026-05-25');
    // 2026-05-29 is Friday → still Monday May 25
    expect(toISODate(startOfWeek(new Date(2026, 4, 29)))).toBe('2026-05-25');
    // 2026-05-31 is Sunday → previous Monday May 25
    expect(toISODate(startOfWeek(new Date(2026, 4, 31)))).toBe('2026-05-25');
  });
});

describe('addDays', () => {
  it('adds and subtracts', () => {
    const d = new Date(2026, 4, 25);
    expect(toISODate(addDays(d, 7))).toBe('2026-06-01');
    expect(toISODate(addDays(d, -1))).toBe('2026-05-24');
  });
});

describe('dayKeyForDate', () => {
  it('returns mon..sun keys', () => {
    expect(dayKeyForDate(new Date(2026, 4, 25))).toBe('mon');
    expect(dayKeyForDate(new Date(2026, 4, 31))).toBe('sun');
  });
});

describe('isSameDay', () => {
  it('compares only year/month/date', () => {
    const a = new Date(2026, 4, 25, 9, 0);
    const b = new Date(2026, 4, 25, 23, 59);
    expect(isSameDay(a, b)).toBe(true);
    expect(isSameDay(a, addDays(a, 1))).toBe(false);
  });
});

describe('ageInMonths / ageString', () => {
  it('handles whole months', () => {
    expect(ageInMonths('2024-05-25', new Date(2026, 4, 25))).toBe(24);
    expect(ageString('2024-05-25', new Date(2026, 4, 25))).toBe('2 years');
  });
  it('handles incomplete final month', () => {
    expect(ageInMonths('2024-05-26', new Date(2026, 4, 25))).toBe(23);
  });
});

describe('getCalendarMonth', () => {
  it('produces 6 weeks of 7 days', () => {
    const grid = getCalendarMonth(2026, 4);
    expect(grid.length).toBe(6);
    expect(grid[0]?.length).toBe(7);
  });
});

describe('time conversions', () => {
  it('round-trips time strings', () => {
    expect(timeToMinutes('09:30')).toBe(570);
    expect(minutesToTime(570)).toBe('09:30');
    expect(minutesToTime(0)).toBe('00:00');
  });
});

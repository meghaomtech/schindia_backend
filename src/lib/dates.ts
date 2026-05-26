import type { DayKey } from './types';

export const DAY_KEYS: DayKey[] = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'];
export const DAY_LABELS: Record<DayKey, string> = {
  mon: 'Mon',
  tue: 'Tue',
  wed: 'Wed',
  thu: 'Thu',
  fri: 'Fri',
  sat: 'Sat',
  sun: 'Sun',
};

const MONTH_SHORT = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const MONTH_LONG = ['January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December'];

export function pad2(n: number): string {
  return n < 10 ? `0${n}` : `${n}`;
}

export function toISODate(d: Date): string {
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`;
}

export function fromISODate(s: string): Date {
  const [y, m, d] = s.split('-').map(Number);
  return new Date(y, (m ?? 1) - 1, d ?? 1);
}

export function startOfWeek(date: Date): Date {
  const d = new Date(date);
  const day = d.getDay();
  const diff = day === 0 ? -6 : 1 - day; // Monday-based
  d.setDate(d.getDate() + diff);
  d.setHours(0, 0, 0, 0);
  return d;
}

export function addDays(date: Date, n: number): Date {
  const d = new Date(date);
  d.setDate(d.getDate() + n);
  return d;
}

export function dayKeyForDate(date: Date): DayKey {
  const idx = (date.getDay() + 6) % 7;
  return DAY_KEYS[idx]!;
}

export function formatShortDate(date: Date): string {
  return `${date.getDate()} ${MONTH_SHORT[date.getMonth()]}`;
}

export function formatLongDate(date: Date): string {
  return `${date.getDate()} ${MONTH_LONG[date.getMonth()]} ${date.getFullYear()}`;
}

export function formatWeekRange(weekStart: Date): string {
  const end = addDays(weekStart, 6);
  return `${formatShortDate(weekStart)} – ${formatShortDate(end)}`;
}

export function isSameDay(a: Date, b: Date): boolean {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  );
}

export function ageString(dobISO: string, on: Date = new Date()): string {
  const dob = fromISODate(dobISO);
  let years = on.getFullYear() - dob.getFullYear();
  let months = on.getMonth() - dob.getMonth();
  if (on.getDate() < dob.getDate()) months -= 1;
  if (months < 0) {
    years -= 1;
    months += 12;
  }
  if (years <= 0) return `${Math.max(0, years * 12 + months)} months`;
  if (months === 0) return `${years} ${years === 1 ? 'year' : 'years'}`;
  return `${years} ${years === 1 ? 'year' : 'years'}, ${months} ${months === 1 ? 'month' : 'months'}`;
}

export function ageInMonths(dobISO: string, on: Date = new Date()): number {
  const dob = fromISODate(dobISO);
  let months = (on.getFullYear() - dob.getFullYear()) * 12 + (on.getMonth() - dob.getMonth());
  if (on.getDate() < dob.getDate()) months -= 1;
  return Math.max(0, months);
}

export function getCalendarMonth(year: number, month: number): Date[][] {
  const first = new Date(year, month, 1);
  const startOffset = (first.getDay() + 6) % 7; // Monday-based
  const start = addDays(first, -startOffset);
  const weeks: Date[][] = [];
  for (let w = 0; w < 6; w++) {
    const row: Date[] = [];
    for (let d = 0; d < 7; d++) row.push(addDays(start, w * 7 + d));
    weeks.push(row);
  }
  return weeks;
}

export function timeToMinutes(t: string): number {
  const [h, m] = t.split(':').map(Number);
  return (h ?? 0) * 60 + (m ?? 0);
}

export function minutesToTime(mins: number): string {
  return `${pad2(Math.floor(mins / 60))}:${pad2(mins % 60)}`;
}

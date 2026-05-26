import {
  addDays,
  dayKeyForDate,
  fromISODate,
  isSameDay,
  startOfWeek,
  toISODate,
} from './dates';
import type { Centre, SessionSlot } from './types';

export interface ProgressMW {
  month: number;
  week: number;
}

/**
 * For a recurring slot, given the slot's starting (M, W) at startDate, return
 * the (M, W) for the week that `viewDate` falls in. Week 4 rolls into Month
 * +1 Week 1, etc. For one-off slots, returns the starting (M, W).
 */
export function progressForWeek(slot: SessionSlot, viewDate: Date): ProgressMW {
  const start: ProgressMW = { month: slot.startingMonth, week: slot.startingWeek };
  if (slot.bookingType !== 'recurring') return start;

  const slotStart = fromISODate(slot.startDate);
  const slotWeekStart = startOfWeek(slotStart);
  const viewWeekStart = startOfWeek(viewDate);
  const elapsedWeeks = Math.round(
    (viewWeekStart.getTime() - slotWeekStart.getTime()) / (7 * 24 * 60 * 60 * 1000)
  );
  if (elapsedWeeks <= 0) return start;

  const weekZeroBased = (slot.startingWeek - 1) + elapsedWeeks;
  const monthOffset = Math.floor(weekZeroBased / 4);
  const weekInMonth = (weekZeroBased % 4) + 1;
  return { month: slot.startingMonth + monthOffset, week: weekInMonth };
}

/**
 * Decide whether a slot should render on a given date in the calendar view.
 * Closed days are excluded. Recurring sessions render on every same-day-of-week
 * occurrence between startDate and endDate (inclusive). One-off renders only
 * on its startDate.
 */
export function slotAppearsOnDate(
  slot: SessionSlot,
  date: Date,
  centre: Centre
): boolean {
  if (centre.closureDates.includes(toISODate(date))) return false;

  const dk = dayKeyForDate(date);
  if (centre.openingTimes[dk] && !centre.openingTimes[dk].open) return false;

  const start = fromISODate(slot.startDate);

  if (slot.bookingType === 'one-off') {
    return isSameDay(date, start);
  }

  if (!slot.endDate) return false;
  const end = fromISODate(slot.endDate);

  if (date < start || date > end) return false;
  if (slot.day !== dk) return false;
  return true;
}

/** Return the dates of the 7 days in the week containing `date`. */
export function weekDates(date: Date): Date[] {
  const start = startOfWeek(date);
  return Array.from({ length: 7 }, (_, i) => addDays(start, i));
}

/**
 * Returns true if a candidate slot (placed at `date`/`startTime` for `durationMinutes`)
 * would overlap any existing slot in the same room on the same date. `excludeSlotId`
 * lets callers ignore the slot being edited.
 */
export function hasSlotOverlap(
  args: {
    centre: Centre;
    roomId: string;
    date: Date;
    startMinutes: number;
    durationMinutes: number;
    sessionsById: Record<string, { durationHours: number; durationMinutes: number }>;
    existingSlots: SessionSlot[];
    excludeSlotId?: string | null;
  }
): boolean {
  const { centre, roomId, date, startMinutes, durationMinutes, sessionsById, existingSlots, excludeSlotId } = args;
  const candidateEnd = startMinutes + durationMinutes;
  for (const s of existingSlots) {
    if (s.roomId !== roomId) continue;
    if (s.centreId !== centre.id) continue;
    if (excludeSlotId && s.id === excludeSlotId) continue;
    if (!slotAppearsOnDate(s, date, centre)) continue;
    const sess = sessionsById[s.sessionId];
    if (!sess) continue;
    const start = timeMinutes(s.startTime);
    const end = start + sess.durationHours * 60 + sess.durationMinutes;
    if (start < candidateEnd && end > startMinutes) return true;
  }
  return false;
}

function timeMinutes(t: string): number {
  const [h, m] = t.split(':').map(Number);
  return (h ?? 0) * 60 + (m ?? 0);
}

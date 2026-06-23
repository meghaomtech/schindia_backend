import { useMemo } from 'react';
import { Badge } from '@/components/ui/Badge';
import { ChildrenIcon, RecurringIcon, UserIcon } from '@/components/ui/icons';
import {
  DAY_LABELS,
  addDays,
  dayKeyForDate,
  isSameDay,
  minutesToTime,
  startOfWeek,
  timeToMinutes,
  toISODate,
  formatShortDate,
} from '@/lib/dates';
import { progressForWeek, slotAppearsOnDate } from '@/lib/recurrence';
import type {
  Centre,
  Room,
  Session,
  SessionSlot,
  Teacher,
} from '@/lib/types';

const SLOT_PX = 60; // px per hour (spec: exactly 60px)
const HEADER_PX = 56;

export interface WeekGridProps {
  centre: Centre;
  room: Room;
  weekDate: Date;
  sessions: Session[];
  slots: SessionSlot[];
  teachers?: Teacher[];
  onCellClick: (date: Date, time: string) => void;
  onSlotClick: (slot: SessionSlot, date: Date) => void;
}

export function WeekGrid({
  centre,
  room,
  weekDate,
  sessions,
  slots,
  teachers = [],
  onCellClick,
  onSlotClick,
}: WeekGridProps) {
  const weekStart = startOfWeek(weekDate);
  const days = Array.from({ length: 7 }, (_, i) => addDays(weekStart, i));
  const today = new Date();

  const { earliest, latest } = useMemo(() => {
    let e = 24 * 60;
    let l = 0;
    for (const d of days) {
      const dk = dayKeyForDate(d);
      const ot = centre.openingTimes[dk];
      if (!ot.open) continue;
      const o = timeToMinutes(ot.opensAt);
      const c = timeToMinutes(ot.closesAt);
      if (o < e) e = o;
      if (c > l) l = c;
    }
    if (l <= e) { e = 7 * 60; l = 18 * 60; }
    return { earliest: Math.floor(e / 60) * 60, latest: Math.ceil(l / 60) * 60 };
  }, [centre.openingTimes, weekStart.getTime()]);

  const totalMinutes = latest - earliest;
  const totalPx = (totalMinutes / 60) * SLOT_PX;
  const hourTicks = Array.from(
    { length: Math.ceil(totalMinutes / 60) + 1 },
    (_, i) => earliest + i * 60
  );

  const slotsForRoom = slots.filter(
    (s) => s.centreId === centre.id && s.roomId === room.id
  );

  const teacherById = useMemo(() => {
    const m: Record<string, Teacher> = {};
    for (const t of teachers) m[t.id] = t;
    return m;
  }, [teachers]);

  return (
    <div className="card overflow-x-auto">
      <div className="min-w-[800px]">
        <div className="grid" style={{ gridTemplateColumns: '64px repeat(7, 1fr)' }}>
          <div style={{ height: HEADER_PX }} />
          {days.map((d) => {
            const dk = dayKeyForDate(d);
            const isClosure = centre.closureDates.includes(toISODate(d));
            const closed = !centre.openingTimes[dk].open || isClosure;
            const isToday = isSameDay(d, today);
            return (
              <div
                key={d.toISOString()}
                style={{ height: HEADER_PX }}
                className={[
                  'border-l border-b border-border px-2 flex flex-col justify-center text-sm',
                  closed ? 'striped-bg text-text-dim' : '',
                  isToday && !closed ? 'bg-info/10' : '',
                ].join(' ')}
              >
                <span className="font-semibold">{DAY_LABELS[dk]}</span>
                {closed ? (
                  <Badge tone="default" className="self-start mt-0.5">Closed</Badge>
                ) : (
                  <span className="text-xs text-text-muted">{formatShortDate(d)}</span>
                )}
              </div>
            );
          })}
        </div>

        <div className="relative grid" style={{ gridTemplateColumns: '64px repeat(7, 1fr)' }}>
          <div className="relative" style={{ height: totalPx }}>
            {hourTicks.map((m) => (
              <div
                key={m}
                className="absolute right-1 -translate-y-1/2 text-xs text-text-muted"
                style={{ top: ((m - earliest) / 60) * SLOT_PX }}
              >
                {minutesToTime(m)}
              </div>
            ))}
          </div>

          {days.map((d) => {
            const dk = dayKeyForDate(d);
            const ot = centre.openingTimes[dk];
            const isClosure = centre.closureDates.includes(toISODate(d));
            const closed = !ot.open || isClosure;
            const isToday = isSameDay(d, today);

            const dayOpenStart = ot.open ? timeToMinutes(ot.opensAt) : earliest;
            const dayOpenEnd = ot.open ? timeToMinutes(ot.closesAt) : earliest;

            const daySlots = slotsForRoom.filter((s) =>
              slotAppearsOnDate(s, d, centre)
            );

            const beforeOpenH = Math.max(0, ((dayOpenStart - earliest) / 60) * SLOT_PX);
            const afterOpenH = Math.max(0, ((latest - dayOpenEnd) / 60) * SLOT_PX);

            return (
              <div
                key={d.toISOString()}
                className={[
                  'relative border-l border-border',
                  closed
                    ? 'striped-bg pointer-events-none'
                    : 'cursor-pointer hover:bg-info/5',
                  isToday && !closed ? 'bg-info/[0.04]' : '',
                ].join(' ')}
                style={{ height: totalPx }}
                onClick={(e) => {
                  if (closed) return;
                  if ((e.target as HTMLElement).dataset.slot) return;
                  const rect = (e.currentTarget as HTMLDivElement).getBoundingClientRect();
                  const y = e.clientY - rect.top;
                  const totalMin =
                    earliest + Math.floor((y / SLOT_PX) * 60 / 30) * 30;
                  // clamp to opening hours
                  if (totalMin < dayOpenStart || totalMin >= dayOpenEnd) return;
                  onCellClick(d, minutesToTime(totalMin));
                }}
              >
                {/* dim out non-open portions of the day on partially-open days */}
                {!closed && beforeOpenH > 0 && (
                  <div
                    className="absolute left-0 right-0 striped-bg pointer-events-none"
                    style={{ top: 0, height: beforeOpenH }}
                  />
                )}
                {!closed && afterOpenH > 0 && (
                  <div
                    className="absolute left-0 right-0 striped-bg pointer-events-none"
                    style={{ bottom: 0, height: afterOpenH }}
                  />
                )}

                {hourTicks.slice(1, -1).map((m) => (
                  <div
                    key={m}
                    className="absolute left-0 right-0 border-t border-border/50"
                    style={{ top: ((m - earliest) / 60) * SLOT_PX }}
                  />
                ))}

                {daySlots.map((slot) => {
                  const session = sessions.find((s) => s.id === slot.sessionId);
                  if (!session) return null;
                  const startMin = timeToMinutes(slot.startTime);
                  const dur = session.durationHours * 60 + session.durationMinutes;
                  const top = ((startMin - earliest) / 60) * SLOT_PX;
                  const height = (dur / 60) * SLOT_PX;
                  const prog = progressForWeek(slot, d);
                  const recurring = slot.bookingType === 'recurring';

                  const showAll = height >= 96;
                  const showSome = height >= 60 && height < 96;
                  const showCompact = height < 60;

                  const firstTeacher =
                    slot.teacherIds[0] && teacherById[slot.teacherIds[0]]?.name;
                  const extraTeachers =
                    slot.teacherIds.length > 1 ? slot.teacherIds.length - 1 : 0;

                  return (
                    <div
                      key={slot.id}
                      data-slot="1"
                      onClick={(e) => {
                        e.stopPropagation();
                        onSlotClick(slot, d);
                      }}
                      className="absolute left-1 right-1 rounded-md p-1.5 text-xs shadow-sm overflow-hidden cursor-pointer hover:shadow-md flex flex-col"
                      style={{
                        top,
                        height,
                        background: session.colorBg,
                        color: session.colorText,
                      }}
                      role="button"
                      aria-label={`${session.name} at ${slot.startTime}`}
                    >
                      <div className="font-semibold leading-tight truncate">
                        {session.name}
                      </div>
                      {!showCompact && firstTeacher && (
                        <div className="truncate opacity-90 flex items-center gap-1">
                          <UserIcon width={11} height={11} className="shrink-0" />
                          <span className="truncate">
                            {firstTeacher}
                            {extraTeachers > 0 && ` +${extraTeachers}`}
                          </span>
                        </div>
                      )}
                      {(showAll || showSome) && (
                        <div className="opacity-90 flex items-center gap-1">
                          <ChildrenIcon width={11} height={11} className="shrink-0" />
                          <span>
                            {slot.childIds.length}/{session.childLimit}
                          </span>
                        </div>
                      )}
                      {showAll && (
                        <div className="opacity-80">
                          {recurring
                            ? `M${prog.month} W${prog.week}`
                            : slot.startTime}
                        </div>
                      )}
                      {recurring && height >= 80 && (
                        <div className="mt-auto opacity-70 text-[10px] flex items-center gap-1">
                          <RecurringIcon width={11} height={11} className="shrink-0" />
                          <span>Recurring</span>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

import { useEffect, useMemo, useState } from 'react';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { EmptyState } from '@/components/ui/EmptyState';
import { useStore } from '@/store/store';
import {
  DAY_LABELS,
  addDays,
  dayKeyForDate,
  formatShortDate,
  formatWeekRange,
  minutesToTime,
  startOfWeek,
  timeToMinutes,
  toISODate,
  isSameDay,
} from '@/lib/dates';
import { progressForWeek, slotAppearsOnDate } from '@/lib/recurrence';
import { WeekGrid } from './WeekGrid';
import { SlotModal } from './SlotModal';
import { GenerateTimetableModal } from './GenerateTimetableModal';
import type { SlotModalCtx } from './SlotModal';
import type { Centre, Room, Session, SessionSlot } from '@/lib/types';

type ViewMode = 'all-rooms' | 'by-room' | 'by-session';

const SLOT_PX = 60;
const HEADER_PX = 56;

export function SchedulePage({ centre }: { centre: Centre }) {
  const { sessions, slots, roles } = useStore();
  const [viewMode, setViewMode] = useState<ViewMode>('all-rooms');
  const [roomId, setRoomId] = useState<string | null>(centre.rooms[0]?.id ?? null);
  const [sessionFilter, setSessionFilter] = useState<string>('all');
  const [weekDate, setWeekDate] = useState(() => startOfWeek(new Date()));
  const [modalCtx, setModalCtx] = useState<SlotModalCtx | null>(null);
  const [showGenerateModal, setShowGenerateModal] = useState(false);

  // Derive teachers from "Teacher" role members for this centre
  const teachers = useMemo(() => {
    const teacherRole = roles.find(
      (r) => r.centreId === centre.id && r.name === 'Teacher'
    );
    return (teacherRole?.members ?? []).map((m) => ({ id: m.id, name: m.name }));
  }, [roles, centre.id]);

  useEffect(() => {
    if (!roomId || !centre.rooms.find((r) => r.id === roomId)) {
      setRoomId(centre.rooms[0]?.id ?? null);
    }
  }, [centre, roomId]);

  const room = useMemo(
    () => centre.rooms.find((r) => r.id === roomId) ?? null,
    [centre, roomId]
  );

  const centreSessions = useMemo(
    () => sessions.filter((s) => s.centreId === centre.id),
    [sessions, centre.id]
  );

  const centreSlots = useMemo(
    () => slots.filter((s) => s.centreId === centre.id),
    [slots, centre.id]
  );

  const weekStart = startOfWeek(weekDate);
  const weekDays = useMemo(
    () => Array.from({ length: 7 }, (_, i) => addDays(weekStart, i)),
    [weekStart.getTime()]
  );

  const allWeekClosed = useMemo(() => {
    return weekDays.every((d) => {
      const dk = dayKeyForDate(d);
      const ot = centre.openingTimes[dk];
      const isClosure = centre.closureDates.includes(toISODate(d));
      return !ot.open || isClosure;
    });
  }, [centre, weekDays]);

  function shiftWeek(weeks: number) {
    setWeekDate((d) => addDays(d, weeks * 7));
  }

  function openCellModal(date: Date, time: string, targetRoom?: Room) {
    const r = targetRoom ?? room;
    if (!r) return;
    setModalCtx({
      centre,
      room: r,
      date,
      startTime: time,
      existingSlot: null,
    });
  }

  function openSlotModal(slot: SessionSlot, date: Date) {
    const slotRoom = centre.rooms.find((r) => r.id === slot.roomId) ?? room;
    if (!slotRoom) return;
    setModalCtx({
      centre,
      room: slotRoom,
      date,
      startTime: slot.startTime,
      existingSlot: slot,
    });
  }

  return (
    <div className="space-y-5">
      <div>
        <div className="text-base font-semibold text-charcoal">
          Timetable for {centre.name}
        </div>
        <div className="text-sm text-text-muted">
          Plan recurring and one-off sessions for each room.
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Button variant="primary" onClick={() => setShowGenerateModal(true)} className="h-8 py-0">
          + Create Timetable
        </Button>

        <Select
          aria-label="View mode"
          value={viewMode}
          onChange={(e) => setViewMode(e.target.value as ViewMode)}
          className="h-8 py-0 w-auto"
        >
          <option value="all-rooms">All rooms</option>
          <option value="by-room">By room</option>
          <option value="by-session">By session</option>
        </Select>

        {viewMode === 'by-room' && (
          <Select
            aria-label="Room"
            value={roomId ?? ''}
            onChange={(e) => setRoomId(e.target.value)}
            disabled={centre.rooms.length === 0}
            className="h-8 py-0 w-auto"
          >
            {centre.rooms.length === 0 ? (
              <option value="">No rooms</option>
            ) : (
              centre.rooms.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name}
                </option>
              ))
            )}
          </Select>
        )}

        {viewMode === 'by-session' && (
          <Select
            aria-label="Session"
            value={sessionFilter}
            onChange={(e) => setSessionFilter(e.target.value)}
            className="h-8 py-0 w-auto"
          >
            <option value="all">All sessions</option>
            {centreSessions.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </Select>
        )}

        <div className="flex items-center gap-1 ml-auto">
          <Button
            onClick={() => shiftWeek(-1)}
            aria-label="Previous week"
            className="h-8 py-0"
          >
            ←
          </Button>
          <span className="font-semibold text-sm px-2 min-w-[140px] text-center">
            {formatWeekRange(weekStart)}
          </span>
          <Button
            onClick={() => shiftWeek(1)}
            aria-label="Next week"
            className="h-8 py-0"
          >
            →
          </Button>
          <Button
            onClick={() => setWeekDate(startOfWeek(new Date()))}
            className="h-8 py-0"
          >
            Today
          </Button>
        </div>
      </div>

      {centre.rooms.length === 0 ? (
        <EmptyState
          title="No rooms in this centre"
          description="Add rooms in Centre details to start scheduling."
        />
      ) : allWeekClosed ? (
        <EmptyState
          title="No sessions available this week — this is a closure period."
        />
      ) : viewMode === 'all-rooms' ? (
        <AllRoomsGrid
          centre={centre}
          weekDays={weekDays}
          weekStart={weekStart}
          sessions={centreSessions}
          slots={centreSlots}
          onCellClick={openCellModal}
          onSlotClick={openSlotModal}
        />
      ) : viewMode === 'by-session' ? (
        <BySessionView
          centre={centre}
          weekDays={weekDays}
          sessions={centreSessions}
          slots={centreSlots}
          sessionFilter={sessionFilter}
          onSlotClick={openSlotModal}
        />
      ) : room ? (
        <WeekGrid
          centre={centre}
          room={room}
          weekDate={weekDate}
          sessions={centreSessions}
          slots={centreSlots}
          teachers={teachers}
          onCellClick={openCellModal}
          onSlotClick={openSlotModal}
        />
      ) : (
        <EmptyState
          title="No rooms in this centre"
          description="Add rooms in Centre details to start scheduling."
        />
      )}

      <SlotModal
        ctx={modalCtx}
        allSlots={slots}
        onClose={() => setModalCtx(null)}
      />

      <GenerateTimetableModal
        open={showGenerateModal}
        centre={centre}
        onClose={() => setShowGenerateModal(false)}
      />
    </div>
  );
}

interface AllRoomsGridProps {
  centre: Centre;
  weekDays: Date[];
  weekStart: Date;
  sessions: Session[];
  slots: SessionSlot[];
  onCellClick: (date: Date, time: string, room?: Room) => void;
  onSlotClick: (slot: SessionSlot, date: Date) => void;
}

interface PositionedSlot {
  slot: SessionSlot;
  session: Session;
  room: Room;
  startMin: number;
  endMin: number;
  col: number;
  totalCols: number;
}

function layoutOverlaps(items: { startMin: number; endMin: number }[]): { col: number; totalCols: number }[] {
  if (items.length === 0) return [];
  const sorted = items.map((it, idx) => ({ ...it, idx })).sort((a, b) => a.startMin - b.startMin || a.endMin - b.endMin);
  const cols: number[] = new Array(items.length).fill(0);
  const ends: number[] = [];

  for (const item of sorted) {
    let placed = false;
    for (let c = 0; c < ends.length; c++) {
      if (ends[c] <= item.startMin) {
        cols[item.idx] = c;
        ends[c] = item.endMin;
        placed = true;
        break;
      }
    }
    if (!placed) {
      cols[item.idx] = ends.length;
      ends.push(item.endMin);
    }
  }

  const totalCols = ends.length;
  return items.map((_, idx) => ({ col: cols[idx], totalCols }));
}

function AllRoomsGrid({ centre, weekDays, weekStart, sessions, slots, onCellClick, onSlotClick }: AllRoomsGridProps) {
  const today = new Date();
  const centreSlots = slots.filter((s) => s.centreId === centre.id);

  const sessionById = useMemo(() => {
    const m: Record<string, Session> = {};
    for (const s of sessions) m[s.id] = s;
    return m;
  }, [sessions]);

  const roomById = useMemo(() => {
    const m: Record<string, Room> = {};
    for (const r of centre.rooms) m[r.id] = r;
    return m;
  }, [centre.rooms]);

  const { earliest, latest } = useMemo(() => {
    let e = 24 * 60;
    let l = 0;
    for (const d of weekDays) {
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

  return (
    <div className="card overflow-x-auto">
      <div className="min-w-[800px]">
        {/* Header */}
        <div className="grid" style={{ gridTemplateColumns: '64px repeat(7, 1fr)' }}>
          <div style={{ height: HEADER_PX }} />
          {weekDays.map((d) => {
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

        {/* Time grid body */}
        <div className="relative grid" style={{ gridTemplateColumns: '64px repeat(7, 1fr)' }}>
          {/* Time labels */}
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

          {/* Day columns */}
          {weekDays.map((d) => {
            const dk = dayKeyForDate(d);
            const ot = centre.openingTimes[dk];
            const isClosure = centre.closureDates.includes(toISODate(d));
            const closed = !ot.open || isClosure;
            const isToday = isSameDay(d, today);

            const dayOpenStart = ot.open ? timeToMinutes(ot.opensAt) : earliest;
            const dayOpenEnd = ot.open ? timeToMinutes(ot.closesAt) : earliest;

            const daySlots = centreSlots.filter((s) => slotAppearsOnDate(s, d, centre));

            const items = daySlots.map((slot) => {
              const session = sessionById[slot.sessionId];
              if (!session) return null;
              const startMin = timeToMinutes(slot.startTime);
              const dur = session.durationHours * 60 + session.durationMinutes;
              return { slot, session, room: roomById[slot.roomId], startMin, endMin: startMin + dur };
            }).filter(Boolean) as { slot: SessionSlot; session: Session; room: Room; startMin: number; endMin: number }[];

            const layout = layoutOverlaps(items);
            const positioned: PositionedSlot[] = items.map((it, i) => ({
              ...it,
              col: layout[i].col,
              totalCols: layout[i].totalCols,
            }));

            const beforeOpenH = Math.max(0, ((dayOpenStart - earliest) / 60) * SLOT_PX);
            const afterOpenH = Math.max(0, ((latest - dayOpenEnd) / 60) * SLOT_PX);

            return (
              <div
                key={d.toISOString()}
                className={[
                  'relative border-l border-border',
                  closed
                    ? 'striped-bg pointer-events-none'
                    : 'cursor-pointer hover:bg-info/[0.03]',
                  isToday && !closed ? 'bg-info/[0.04]' : '',
                ].join(' ')}
                style={{ height: totalPx }}
                onClick={(e) => {
                  if (closed) return;
                  if ((e.target as HTMLElement).closest('[data-slot]')) return;
                  const rect = (e.currentTarget as HTMLDivElement).getBoundingClientRect();
                  const y = e.clientY - rect.top;
                  const totalMin = earliest + Math.floor((y / SLOT_PX) * 60 / 30) * 30;
                  if (totalMin < dayOpenStart || totalMin >= dayOpenEnd) return;
                  onCellClick(d, minutesToTime(totalMin), centre.rooms[0]);
                }}
              >
                {/* Closed portions */}
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

                {/* Hour lines */}
                {hourTicks.slice(1, -1).map((m) => (
                  <div
                    key={m}
                    className="absolute left-0 right-0 border-t border-border/50"
                    style={{ top: ((m - earliest) / 60) * SLOT_PX }}
                  />
                ))}

                {/* Session blocks — side-by-side like Outlook */}
                {positioned.map((p) => {
                  const top = ((p.startMin - earliest) / 60) * SLOT_PX;
                  const height = ((p.endMin - p.startMin) / 60) * SLOT_PX;
                  const widthPct = 100 / p.totalCols;
                  const leftPct = p.col * widthPct;
                  const endTime = minutesToTime(p.endMin);
                  const prog = p.slot.bookingType === 'recurring' ? progressForWeek(p.slot, d) : null;

                  return (
                    <div
                      key={p.slot.id}
                      data-slot="1"
                      onClick={(e) => {
                        e.stopPropagation();
                        onSlotClick(p.slot, d);
                      }}
                      className="absolute rounded-md p-1.5 text-xs shadow-sm overflow-hidden cursor-pointer hover:shadow-md flex flex-col border border-white/40"
                      style={{
                        top,
                        height,
                        left: `calc(${leftPct}% + 2px)`,
                        width: `calc(${widthPct}% - 4px)`,
                        background: p.session.colorBg,
                        color: p.session.colorText,
                      }}
                      role="button"
                      aria-label={`${p.session.name} in ${p.room?.name} at ${p.slot.startTime}`}
                    >
                      <div className="font-semibold leading-tight truncate">
                        {p.session.name}
                      </div>
                      {height >= 40 && (
                        <div className="opacity-80 text-[10px] truncate">
                          {p.slot.startTime} – {endTime}
                        </div>
                      )}
                      {height >= 55 && p.room && (
                        <div className="opacity-70 text-[10px] truncate">
                          📍 {p.room.name}
                        </div>
                      )}
                      {height >= 70 && (
                        <div className="opacity-70 text-[10px]">
                          {p.slot.childIds.length}/{p.session.childLimit} children
                        </div>
                      )}
                      {prog && height >= 40 && (
                        <div className="opacity-80 text-[10px] font-medium">
                          M{prog.month}W{prog.week}
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

interface BySessionViewProps {
  centre: Centre;
  weekDays: Date[];
  sessions: Session[];
  slots: SessionSlot[];
  sessionFilter: string;
  onSlotClick: (slot: SessionSlot, date: Date) => void;
}

function BySessionView({ centre, weekDays, sessions, slots, sessionFilter, onSlotClick }: BySessionViewProps) {
  const centreSlots = slots.filter((s) => s.centreId === centre.id);
  const filteredSessions = sessionFilter === 'all' ? sessions : sessions.filter((s) => s.id === sessionFilter);
  const roomById = useMemo(() => {
    const m: Record<string, Room> = {};
    for (const r of centre.rooms) m[r.id] = r;
    return m;
  }, [centre.rooms]);

  return (
    <div className="card overflow-x-auto">
      <div className="min-w-[800px]">
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="border-b border-border bg-bg-elev">
              <th className="text-left px-3 py-2.5 font-medium text-text-muted w-[100px]">Session</th>
              {weekDays.map((d) => {
                const dk = dayKeyForDate(d);
                const ot = centre.openingTimes[dk];
                const isClosure = centre.closureDates.includes(toISODate(d));
                const closed = !ot.open || isClosure;
                return (
                  <th
                    key={d.toISOString()}
                    className={[
                      'text-left px-3 py-2.5 font-medium border-l border-border',
                      closed ? 'text-text-dim striped-bg' : '',
                    ].join(' ')}
                  >
                    <div className="font-semibold">{DAY_LABELS[dk]}</div>
                    <div className="text-xs text-text-muted font-normal">
                      {closed ? 'Closed' : formatShortDate(d)}
                    </div>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {filteredSessions.map((session) => {
              const sessionSlots = centreSlots.filter((s) => s.sessionId === session.id);
              return (
                <tr key={session.id} className="border-b border-border">
                  <td className="px-3 py-2 align-top">
                    <div className="flex items-center gap-2">
                      <span
                        className="w-3 h-3 rounded-full shrink-0"
                        style={{ background: session.colorBg, border: `1px solid ${session.colorText}` }}
                      />
                      <div>
                        <div className="font-medium text-text">{session.name}</div>
                        <div className="text-[10px] text-text-muted">
                          {session.ageFrom}–{session.ageTo} {session.ageUnit}
                        </div>
                      </div>
                    </div>
                  </td>
                  {weekDays.map((d) => {
                    const dk = dayKeyForDate(d);
                    const ot = centre.openingTimes[dk];
                    const isClosure = centre.closureDates.includes(toISODate(d));
                    const closed = !ot.open || isClosure;
                    const daySlots = sessionSlots.filter((s) => slotAppearsOnDate(s, d, centre));
                    const sorted = [...daySlots].sort(
                      (a, b) => timeToMinutes(a.startTime) - timeToMinutes(b.startTime)
                    );

                    return (
                      <td
                        key={d.toISOString()}
                        className={[
                          'px-2 py-2 border-l border-border align-top',
                          closed ? 'striped-bg' : '',
                        ].join(' ')}
                      >
                        {closed ? (
                          <span className="text-xs text-text-dim">—</span>
                        ) : sorted.length === 0 ? (
                          <span className="text-xs text-text-dim italic">—</span>
                        ) : (
                          <div className="space-y-1.5">
                            {sorted.map((slot) => {
                              const dur = session.durationHours * 60 + session.durationMinutes;
                              const endTime = minutesToTime(timeToMinutes(slot.startTime) + dur);
                              const roomName = roomById[slot.roomId]?.name ?? '?';
                              return (
                                <button
                                  key={slot.id}
                                  onClick={() => onSlotClick(slot, d)}
                                  className="w-full text-left rounded-md px-2 py-1.5 text-xs cursor-pointer hover:shadow-md transition-shadow"
                                  style={{ background: session.colorBg, color: session.colorText }}
                                >
                                  <div className="font-semibold">{slot.startTime} – {endTime}</div>
                                  <div className="opacity-80">
                                    <Badge tone="beige" className="text-[9px] px-1 py-0">{roomName}</Badge>
                                  </div>
                                  <div className="opacity-70 text-[10px] mt-0.5">
                                    {slot.childIds.length}/{session.childLimit} children
                                  </div>
                                </button>
                              );
                            })}
                          </div>
                        )}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

import { useEffect, useMemo, useState } from 'react';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Input';
import { EmptyState } from '@/components/ui/EmptyState';
import { useStore } from '@/store/store';
import {
  addDays,
  dayKeyForDate,
  formatWeekRange,
  startOfWeek,
  toISODate,
} from '@/lib/dates';
import { WeekGrid } from './WeekGrid';
import { SlotModal } from './SlotModal';
import type { SlotModalCtx } from './SlotModal';
import type { SessionSlot } from '@/lib/types';

export function SchedulePage() {
  const { centres, sessions, slots, teachers } = useStore();
  const [centreId, setCentreId] = useState(centres[0]?.id ?? '');
  const [roomId, setRoomId] = useState<string | null>(null);
  const [weekDate, setWeekDate] = useState(() => startOfWeek(new Date()));
  const [modalCtx, setModalCtx] = useState<SlotModalCtx | null>(null);

  const centre = useMemo(
    () => centres.find((c) => c.id === centreId) ?? centres[0] ?? null,
    [centres, centreId]
  );

  useEffect(() => {
    if (!centre) {
      setRoomId(null);
      return;
    }
    if (!roomId || !centre.rooms.find((r) => r.id === roomId)) {
      setRoomId(centre.rooms[0]?.id ?? null);
    }
  }, [centre, roomId]);

  const room = useMemo(
    () => centre?.rooms.find((r) => r.id === roomId) ?? null,
    [centre, roomId]
  );

  const weekStart = startOfWeek(weekDate);
  const weekDays = useMemo(
    () => Array.from({ length: 7 }, (_, i) => addDays(weekStart, i)),
    [weekStart.getTime()]
  );

  const allWeekClosed = useMemo(() => {
    if (!centre) return true;
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

  function openCellModal(date: Date, time: string) {
    if (!centre || !room) return;
    setModalCtx({
      centre,
      room,
      date,
      startTime: time,
      existingSlot: null,
    });
  }

  function openSlotModal(slot: SessionSlot, date: Date) {
    if (!centre || !room) return;
    setModalCtx({
      centre,
      room,
      date,
      startTime: slot.startTime,
      existingSlot: slot,
    });
  }

  if (!centre) {
    return (
      <div className="space-y-5">
        <h1 className="text-xl font-semibold text-charcoal">Weekly schedule</h1>
        <EmptyState
          title="No centres yet"
          description="Add a centre to start scheduling."
        />
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <h1 className="text-xl font-semibold text-charcoal">Weekly schedule</h1>

      <div className="flex flex-wrap items-center gap-2">
        <Select
          aria-label="Centre"
          value={centreId}
          onChange={(e) => {
            setCentreId(e.target.value);
            setRoomId(null);
          }}
          className="h-8 py-0 w-auto"
        >
          {centres.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </Select>
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

      {!room ? (
        <EmptyState
          title="No rooms in this centre"
          description="Add rooms in Centre details to start scheduling."
        />
      ) : allWeekClosed ? (
        <EmptyState
          title="No sessions available this week — this is a closure period."
        />
      ) : (
        <WeekGrid
          centre={centre}
          room={room}
          weekDate={weekDate}
          sessions={sessions}
          slots={slots}
          teachers={teachers}
          onCellClick={openCellModal}
          onSlotClick={openSlotModal}
        />
      )}

      <SlotModal
        ctx={modalCtx}
        allSlots={slots}
        onClose={() => setModalCtx(null)}
      />
    </div>
  );
}

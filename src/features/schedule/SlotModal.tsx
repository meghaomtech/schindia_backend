import { useEffect, useMemo, useState } from 'react';
import { Modal } from '@/components/ui/Modal';
import { Button } from '@/components/ui/Button';
import { Field, Input, Select, Textarea } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { useStore } from '@/store/store';
import { uid } from '@/lib/ids';
import {
  DAY_LABELS,
  dayKeyForDate,
  timeToMinutes,
  toISODate,
} from '@/lib/dates';
import {
  hasSlotOverlap,
  progressForWeek,
} from '@/lib/recurrence';
import type {
  BookingType,
  Centre,
  Room,
  SessionSlot,
} from '@/lib/types';

export interface SlotModalCtx {
  centre: Centre;
  room: Room;
  date: Date;
  startTime: string;
  existingSlot: SessionSlot | null;
}

function durationLabel(h: number, m: number): string {
  if (h > 0 && m > 0) return `${h}hr ${m}min`;
  if (h > 0) return `${h}hr`;
  return `${m}min`;
}

export function SlotModal({
  ctx,
  allSlots,
  onClose,
}: {
  ctx: SlotModalCtx | null;
  allSlots: SessionSlot[];
  onClose: () => void;
}) {
  const {
    sessions,
    teachers,
    children: kids,
    addSlot,
    updateSlot,
    deleteSlot,
  } = useStore();

  const [sessionId, setSessionId] = useState('');
  const [bookingType, setBookingType] = useState<BookingType>('recurring');
  const [startTime, setStartTime] = useState('09:00');
  const [endDate, setEndDate] = useState('');
  const [startingMonth, setStartingMonth] = useState(1);
  const [startingWeek, setStartingWeek] = useState(1);
  const [teacherIds, setTeacherIds] = useState<string[]>([]);
  const [childIds, setChildIds] = useState<string[]>([]);
  const [notes, setNotes] = useState('');
  const [pendingTeacherId, setPendingTeacherId] = useState('');
  const [pendingChildId, setPendingChildId] = useState('');
  const [overlapErr, setOverlapErr] = useState<string | null>(null);

  useEffect(() => {
    if (!ctx) return;
    if (ctx.existingSlot) {
      const s = ctx.existingSlot;
      setSessionId(s.sessionId);
      setBookingType(s.bookingType);
      setStartTime(s.startTime);
      setEndDate(s.endDate ?? '');
      setStartingMonth(s.startingMonth);
      setStartingWeek(s.startingWeek);
      setTeacherIds(s.teacherIds);
      setChildIds(s.childIds);
      setNotes(s.notes ?? '');
    } else {
      setSessionId(sessions[0]?.id ?? '');
      setBookingType('recurring');
      setStartTime(ctx.startTime);
      setEndDate('');
      setStartingMonth(1);
      setStartingWeek(1);
      setTeacherIds([]);
      setChildIds([]);
      setNotes('');
    }
    setPendingTeacherId('');
    setPendingChildId('');
    setOverlapErr(null);
  }, [ctx?.existingSlot?.id, ctx?.date.toString(), ctx?.startTime]);

  const session = useMemo(
    () => sessions.find((s) => s.id === sessionId) ?? null,
    [sessions, sessionId]
  );

  const sessionsById = useMemo(() => {
    const m: Record<string, { durationHours: number; durationMinutes: number }> = {};
    for (const s of sessions) m[s.id] = { durationHours: s.durationHours, durationMinutes: s.durationMinutes };
    return m;
  }, [sessions]);

  const availableTeachers = useMemo(
    () => teachers.filter((t) => !teacherIds.includes(t.id)),
    [teachers, teacherIds]
  );

  const availableChildren = useMemo(
    () =>
      kids.filter(
        (c) => !childIds.includes(c.id) && (!ctx || c.centreId === ctx.centre.id)
      ),
    [kids, childIds, ctx]
  );

  if (!ctx) return null;

  const atCapacity = !!session && childIds.length >= session.childLimit;

  // calculate auto-progress for recurring view
  const previewSlot: SessionSlot | null =
    session && bookingType === 'recurring'
      ? {
          id: 'preview',
          centreId: ctx.centre.id,
          roomId: ctx.room.id,
          sessionId: session.id,
          day: dayKeyForDate(ctx.date),
          startTime,
          bookingType,
          startDate: toISODate(ctx.date),
          endDate: endDate || undefined,
          startingMonth,
          startingWeek,
          teacherIds,
          childIds,
          notes,
        }
      : null;
  const autoProgress = previewSlot ? progressForWeek(previewSlot, ctx.date) : null;

  function addTeacher() {
    if (!pendingTeacherId) return;
    setTeacherIds((t) => [...t, pendingTeacherId]);
    setPendingTeacherId('');
  }
  function removeTeacher(id: string) {
    setTeacherIds((t) => t.filter((x) => x !== id));
  }

  function addChild() {
    if (!pendingChildId) return;
    if (atCapacity) return;
    setChildIds((c) => [...c, pendingChildId]);
    setPendingChildId('');
  }
  function removeChild(id: string) {
    setChildIds((c) => c.filter((x) => x !== id));
  }

  function save() {
    if (!ctx) return;
    if (!session) return;

    const startDate = toISODate(ctx.date);
    const day = dayKeyForDate(ctx.date);
    const dur = session.durationHours * 60 + session.durationMinutes;

    const overlap = hasSlotOverlap({
      centre: ctx.centre,
      roomId: ctx.room.id,
      date: ctx.date,
      startMinutes: timeToMinutes(startTime),
      durationMinutes: dur,
      sessionsById,
      existingSlots: allSlots,
      excludeSlotId: ctx.existingSlot?.id ?? null,
    });
    if (overlap) {
      setOverlapErr('This time conflicts with another session in this room. Choose a different time.');
      return;
    }

    if (ctx.existingSlot) {
      updateSlot(ctx.existingSlot.id, {
        sessionId,
        bookingType,
        startTime,
        startDate,
        endDate: bookingType === 'recurring' ? endDate || undefined : undefined,
        startingMonth,
        startingWeek,
        day,
        teacherIds,
        childIds,
        notes,
      });
    } else {
      const slot: SessionSlot = {
        id: uid('slot'),
        centreId: ctx.centre.id,
        roomId: ctx.room.id,
        sessionId,
        day,
        startTime,
        bookingType,
        startDate,
        endDate: bookingType === 'recurring' ? endDate || undefined : undefined,
        startingMonth,
        startingWeek,
        teacherIds,
        childIds,
        notes,
      };
      addSlot(slot);
    }
    onClose();
  }

  function remove() {
    if (!ctx?.existingSlot) return;
    if (confirm('Remove this slot?')) {
      deleteSlot(ctx.existingSlot.id);
      onClose();
    }
  }

  const dayLabel = DAY_LABELS[dayKeyForDate(ctx.date)];
  const title = ctx.existingSlot
    ? `Edit — ${dayLabel} ${startTime}`
    : `Add session — ${startTime}`;

  return (
    <Modal
      open={!!ctx}
      onClose={onClose}
      size="md"
      title={title}
      footer={
        <div className="flex items-center justify-between w-full">
          {ctx.existingSlot ? (
            <Button variant="danger" onClick={remove}>
              Remove slot
            </Button>
          ) : (
            <span />
          )}
          <div className="flex items-center gap-2">
            <Button onClick={onClose}>Cancel</Button>
            <Button variant="primary" onClick={save} disabled={!session}>
              {ctx.existingSlot ? 'Save changes' : 'Add to calendar'}
            </Button>
          </div>
        </div>
      }
    >
      <div className="space-y-4">
        <div className="text-sm text-text-muted flex items-center gap-2">
          <Badge tone="beige">{ctx.centre.name}</Badge>
          <Badge tone="olive">{ctx.room.name}</Badge>
          <Badge tone="default">{toISODate(ctx.date)}</Badge>
        </div>

        {/* Session selector */}
        <Field label="Session" required>
          <Select
            value={sessionId}
            onChange={(e) => setSessionId(e.target.value)}
          >
            <option value="">— Select session —</option>
            {sessions.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </Select>
        </Field>

        {/* Read-only fields driven by selected session */}
        {session && (
          <div className="grid grid-cols-2 gap-3">
            <Field label="Age range" hint="Not editable here">
              <div className="input bg-bg-elev text-text-muted cursor-not-allowed">
                {session.ageFrom}–{session.ageTo} {session.ageUnit}
              </div>
            </Field>
            <Field label="Duration" hint="Not editable here">
              <div className="input bg-bg-elev text-text-muted cursor-not-allowed">
                {durationLabel(session.durationHours, session.durationMinutes)}
              </div>
            </Field>
          </div>
        )}

        {/* Start time */}
        <Field label="Start time" required>
          <Input
            type="time"
            value={startTime}
            onChange={(e) => setStartTime(e.target.value)}
          />
        </Field>

        {/* Booking type */}
        <div>
          <div className="label mb-1">Booking type</div>
          <div className="flex items-center gap-2">
            {(['one-off', 'recurring'] as BookingType[]).map((bt) => (
              <button
                key={bt}
                type="button"
                onClick={() => setBookingType(bt)}
                aria-pressed={bookingType === bt}
                className={[
                  'pill-tab',
                  bookingType === bt ? 'pill-tab-active' : 'pill-tab-idle',
                ].join(' ')}
              >
                {bt === 'one-off' ? 'One-off' : 'Recurring'}
              </button>
            ))}
          </div>
        </div>

        {/* Start / end date — end disabled when one-off */}
        <div className="grid grid-cols-2 gap-3">
          <Field label="Start date">
            <Input value={toISODate(ctx.date)} readOnly />
          </Field>
          <Field
            label="End date"
            hint={
              bookingType === 'recurring'
                ? 'Last day this slot recurs'
                : 'Disabled — one-off bookings only run on the start date'
            }
          >
            <Input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              disabled={bookingType !== 'recurring'}
            />
          </Field>
        </div>

        {/* Teachers — pills + dropdown + add */}
        <div>
          <div className="label mb-1">Teachers</div>
          <div className="flex flex-wrap gap-1.5 mb-2">
            {teacherIds.length === 0 && (
              <span className="text-xs text-text-dim italic">No teachers added.</span>
            )}
            {teacherIds.map((id) => {
              const t = teachers.find((x) => x.id === id);
              if (!t) return null;
              return (
                <Badge key={id} tone="olive">
                  {t.name}
                  <button
                    type="button"
                    onClick={() => removeTeacher(id)}
                    aria-label={`Remove ${t.name}`}
                    className="ml-1"
                  >
                    ✕
                  </button>
                </Badge>
              );
            })}
          </div>
          <div className="flex items-center gap-2">
            <Select
              value={pendingTeacherId}
              onChange={(e) => setPendingTeacherId(e.target.value)}
              disabled={availableTeachers.length === 0}
              aria-label="Select teacher to add"
            >
              <option value="">— Select teacher —</option>
              {availableTeachers.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </Select>
            <Button onClick={addTeacher} disabled={!pendingTeacherId}>
              Add
            </Button>
          </div>
        </div>

        {/* Children — capacity bar + pills + dropdown + add */}
        {session && (
          <div>
            <div className="flex items-center justify-between mb-1">
              <div className="label mb-0">
                Children {childIds.length} / {session.childLimit}
              </div>
            </div>
            <div className="h-2 rounded-full bg-bg-elev overflow-hidden mb-2">
              <div
                className={[
                  'h-full transition-all',
                  atCapacity ? 'bg-danger' : 'bg-info',
                ].join(' ')}
                style={{
                  width: `${Math.min(100, (childIds.length / session.childLimit) * 100)}%`,
                }}
              />
            </div>

            <div className="flex flex-wrap gap-1.5 mb-2">
              {childIds.length === 0 && (
                <span className="text-xs text-text-dim italic">
                  No children added.
                </span>
              )}
              {childIds.map((id) => {
                const c = kids.find((x) => x.id === id);
                if (!c) return null;
                return (
                  <Badge key={id} tone="beige">
                    {c.firstName} {c.lastName}
                    <button
                      type="button"
                      onClick={() => removeChild(id)}
                      aria-label={`Remove ${c.firstName}`}
                      className="ml-1"
                    >
                      ✕
                    </button>
                  </Badge>
                );
              })}
            </div>

            <div className="flex items-center gap-2">
              <Select
                value={pendingChildId}
                onChange={(e) => setPendingChildId(e.target.value)}
                disabled={atCapacity || availableChildren.length === 0}
                aria-label="Select child to add"
              >
                <option value="">— Select child —</option>
                {availableChildren.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.firstName} {c.lastName}
                  </option>
                ))}
              </Select>
              <Button
                onClick={addChild}
                disabled={atCapacity || !pendingChildId}
              >
                Add
              </Button>
            </div>
            {atCapacity && (
              <div className="text-xs text-danger mt-1">
                Session is at capacity
              </div>
            )}
          </div>
        )}

        {/* Progress in course */}
        <div>
          <div className="label mb-1">Progress in course</div>
          <div className="grid grid-cols-2 gap-3">
            <Field>
              <Select
                value={startingMonth}
                onChange={(e) => setStartingMonth(Number(e.target.value))}
                aria-label="Starting month"
              >
                {Array.from({ length: 12 }, (_, i) => i + 1).map((m) => (
                  <option key={m} value={m}>
                    Month {m}
                  </option>
                ))}
              </Select>
            </Field>
            <Field>
              <Select
                value={startingWeek}
                onChange={(e) => setStartingWeek(Number(e.target.value))}
                aria-label="Starting week"
              >
                {[1, 2, 3, 4].map((w) => (
                  <option key={w} value={w}>
                    Week {w}
                  </option>
                ))}
              </Select>
            </Field>
          </div>
          <div className="text-xs text-text-dim mt-1">
            Tracks where this group is in the course for this slot
          </div>
          {bookingType === 'recurring' && autoProgress && (
            <div className="mt-2">
              <Badge tone="olive">
                Progress auto-advances weekly. This week: M{autoProgress.month} W
                {autoProgress.week}
              </Badge>
            </div>
          )}
        </div>

        {/* Notes */}
        <Field label="Notes">
          <Textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={3}
            placeholder="Slot-specific notes..."
            className="resize-y"
          />
        </Field>

        {overlapErr && (
          <div className="text-sm text-danger border border-danger/40 bg-danger/5 rounded-md px-3 py-2">
            {overlapErr}
          </div>
        )}
      </div>
    </Modal>
  );
}

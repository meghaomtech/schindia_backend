import { useMemo, useState } from 'react';
import { Modal } from '@/components/ui/Modal';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Field, Input } from '@/components/ui/Input';
import { useStore } from '@/store/store';
import {
  DAY_LABELS,
  addDays,
  ageInMonths,
  dayKeyForDate,
  formatLongDate,
  formatShortDate,
  formatWeekRange,
  fromISODate,
  isSameDay,
  minutesToTime,
  startOfWeek,
  timeToMinutes,
  toISODate,
} from '@/lib/dates';
import { progressForWeek, slotAppearsOnDate } from '@/lib/recurrence';
import { initialsOf } from '@/lib/colors';
import { uid } from '@/lib/ids';
import type {
  Child,
  Room,
  Session,
  SessionSlot,
} from '@/lib/types';

const SLOT_PX = 60;
const HEADER_PX = 40;

interface SlotModalCtx {
  slot: SessionSlot;
  date: Date;
}

export function ChildBookingsTab({ child }: { child: Child }) {
  const {
    centres,
    sessions,
    slots,
    teachers,
    children: kids,
    enrolments,
    purchases,
    upsertEnrolment,
    removeEnrolment,
    addPurchase,
  } = useStore();
  const [weekDate, setWeekDate] = useState(() => startOfWeek(new Date()));
  const [modalCtx, setModalCtx] = useState<SlotModalCtx | null>(null);

  const centre = centres.find((c) => c.id === child.centreId);

  const ws = startOfWeek(weekDate);
  const days = useMemo(
    () => Array.from({ length: 7 }, (_, i) => addDays(ws, i)),
    [ws.getTime()]
  );

  if (!centre) {
    return <div className="text-sm text-text-dim">Centre not found.</div>;
  }

  const sessionsForCentre = slots.filter((s) => s.centreId === centre.id);

  function shiftWeek(n: number) {
    setWeekDate((d) => addDays(d, n * 7));
  }

  return (
    <div className="space-y-5">
      <div className="card p-5 space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-base font-semibold">Weekly bookings</div>
            <div className="text-xs text-text-muted">
              All rooms in {centre.name}. Tap a session to view or enrol.
            </div>
          </div>
          <div className="flex items-center gap-1">
            <Button onClick={() => shiftWeek(-1)} aria-label="Previous week" className="h-8 py-0">
              ←
            </Button>
            <span className="font-semibold text-sm px-2 min-w-[140px] text-center">
              {formatWeekRange(ws)}
            </span>
            <Button onClick={() => shiftWeek(1)} aria-label="Next week" className="h-8 py-0">
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

        <Legend />

        <div className="space-y-4">
          {centre.rooms.map((room) => (
            <RoomGrid
              key={room.id}
              room={room}
              days={days}
              centre={centre}
              child={child}
              sessions={sessions}
              slots={sessionsForCentre.filter((s) => s.roomId === room.id)}
              onSlotClick={(slot, date) => setModalCtx({ slot, date })}
            />
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <BillPayersSection child={child} />
        <PurchasesSection
          child={child}
          purchases={purchases.filter(() => true).slice(0, 5)}
          onAdd={() => {
            const today = new Date().toISOString().slice(0, 10);
            addPurchase({
              id: uid('pur'),
              kind: 'Consumable',
              name: 'Manual entry',
              date: today,
              amount: 0,
              paid: false,
            });
          }}
        />
      </div>

      {modalCtx && (
        <SlotDetailModal
          ctx={modalCtx}
          child={child}
          centre={centre}
          sessions={sessions}
          teachers={teachers}
          kids={kids}
          enrolments={enrolments}
          onClose={() => setModalCtx(null)}
          onEnrol={(slotId, startDate, endDate, existingId) => {
            upsertEnrolment({
              id: existingId ?? uid('enr'),
              childId: child.id,
              slotId,
              startDate,
              endDate,
            });
            setModalCtx(null);
          }}
          onRemoveEnrolment={(id) => {
            removeEnrolment(id);
            setModalCtx(null);
          }}
        />
      )}
    </div>
  );
}

function Legend() {
  return (
    <div className="flex flex-wrap items-center gap-4 text-xs text-text-muted">
      <span className="flex items-center gap-1.5">
        <span className="w-3 h-3 rounded-sm border-2 border-accent-purple bg-accent-purple-soft" />
        Age-eligible
      </span>
      <span className="flex items-center gap-1.5">
        <span className="w-3 h-3 rounded-sm bg-bg-elev opacity-30 border border-border" />
        Out of range
      </span>
      <span className="flex items-center gap-1.5">
        <span className="w-2 h-2 rounded-full bg-accent-purple" />
        Eligible
      </span>
      <span className="flex items-center gap-1.5">
        <span className="w-2 h-2 rounded-full bg-olive" />
        Enrolled
      </span>
    </div>
  );
}

function RoomGrid({
  room,
  days,
  centre,
  child,
  sessions,
  slots,
  onSlotClick,
}: {
  room: Room;
  days: Date[];
  centre: ReturnType<typeof useStore>['centres'][number];
  child: Child;
  sessions: Session[];
  slots: SessionSlot[];
  onSlotClick: (slot: SessionSlot, date: Date) => void;
}) {
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
    if (l <= e) {
      e = 8 * 60;
      l = 13 * 60;
    }
    return { earliest: Math.floor(e / 60) * 60, latest: Math.ceil(l / 60) * 60 };
  }, [centre.openingTimes, days]);

  const totalMinutes = latest - earliest;
  const totalPx = (totalMinutes / 60) * SLOT_PX;
  const hourTicks = Array.from(
    { length: Math.ceil(totalMinutes / 60) + 1 },
    (_, i) => earliest + i * 60
  );

  return (
    <div className="rounded-lg border border-border bg-bg-card overflow-hidden">
      <div className="px-4 py-2 border-b border-border bg-bg-elev text-sm font-semibold">
        {room.name}
      </div>
      <div className="overflow-x-auto">
        <div className="min-w-[700px]">
          <div className="grid" style={{ gridTemplateColumns: '56px repeat(7, 1fr)' }}>
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
                    'border-l border-b border-border px-2 flex items-center justify-between text-xs',
                    closed ? 'striped-bg text-text-dim' : '',
                    isToday && !closed ? 'bg-accent-purple/10' : '',
                  ].join(' ')}
                >
                  <span className="font-semibold">{DAY_LABELS[dk]}</span>
                  {closed ? (
                    <Badge tone="danger">Closed</Badge>
                  ) : (
                    <span className="text-text-muted">{formatShortDate(d)}</span>
                  )}
                </div>
              );
            })}
          </div>

          <div
            className="relative grid"
            style={{ gridTemplateColumns: '56px repeat(7, 1fr)' }}
          >
            <div className="relative" style={{ height: totalPx }}>
              {hourTicks.map((m) => (
                <div
                  key={m}
                  className="absolute right-1 -translate-y-1/2 text-[10px] text-text-muted"
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

              const daySlots = slots.filter((s) => slotAppearsOnDate(s, d, centre));

              return (
                <div
                  key={d.toISOString()}
                  className={[
                    'relative border-l border-border',
                    closed ? 'striped-bg' : '',
                    isToday && !closed ? 'bg-accent-purple/[0.04]' : '',
                  ].join(' ')}
                  style={{ height: totalPx }}
                >
                  {hourTicks.slice(1, -1).map((m) => (
                    <div
                      key={m}
                      className="absolute left-0 right-0 border-t border-border/50"
                      style={{ top: ((m - earliest) / 60) * SLOT_PX }}
                    />
                  ))}

                  {!closed &&
                    daySlots.map((slot) => {
                      const session = sessions.find((s) => s.id === slot.sessionId);
                      if (!session) return null;
                      const startMin = timeToMinutes(slot.startTime);
                      const dur =
                        session.durationHours * 60 + session.durationMinutes;
                      const top = ((startMin - earliest) / 60) * SLOT_PX;
                      const height = (dur / 60) * SLOT_PX;
                      const eligible = isAgeEligible(child, d, session);
                      const enrolled = slot.childIds.includes(child.id);

                      return (
                        <button
                          key={slot.id}
                          type="button"
                          onClick={() => onSlotClick(slot, d)}
                          className="absolute left-1 right-1 rounded-md p-1.5 text-[11px] shadow-sm overflow-hidden hover:shadow-md text-left flex flex-col"
                          style={{
                            top,
                            height,
                            background: session.colorBg,
                            color: session.colorText,
                            opacity: eligible ? 1 : 0.25,
                            border: eligible
                              ? '2px solid #7c5fbf'
                              : '1px solid rgba(0,0,0,0.1)',
                          }}
                        >
                          <div className="absolute right-1 top-1 flex items-center gap-1">
                            {eligible && (
                              <span
                                className="w-2 h-2 rounded-full bg-accent-purple"
                                aria-label="Eligible"
                              />
                            )}
                            {enrolled && (
                              <span
                                className="w-2 h-2 rounded-full bg-olive"
                                aria-label="Enrolled"
                              />
                            )}
                          </div>
                          <div className="font-semibold leading-tight truncate pr-6">
                            {session.name}
                          </div>
                          {height >= 50 && (
                            <div className="opacity-90 truncate">
                              👶 {slot.childIds.length}/{session.childLimit}
                            </div>
                          )}
                          {height >= 70 && (
                            <div className="opacity-80 truncate">
                              {slot.startTime}
                            </div>
                          )}
                        </button>
                      );
                    })}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

function isAgeEligible(child: Child, date: Date, session: Session): boolean {
  const months = ageInMonths(child.dateOfBirth, date);
  const fromM = session.ageUnit === 'years' ? session.ageFrom * 12 : session.ageFrom;
  const toM = session.ageUnit === 'years' ? session.ageTo * 12 : session.ageTo;
  return months >= fromM && months <= toM;
}

function SlotDetailModal({
  ctx,
  child,
  centre,
  sessions,
  teachers,
  kids,
  enrolments,
  onClose,
  onEnrol,
  onRemoveEnrolment,
}: {
  ctx: SlotModalCtx;
  child: Child;
  centre: ReturnType<typeof useStore>['centres'][number];
  sessions: Session[];
  teachers: ReturnType<typeof useStore>['teachers'];
  kids: Child[];
  enrolments: ReturnType<typeof useStore>['enrolments'];
  onClose: () => void;
  onEnrol: (slotId: string, startDate: string, endDate: string, existingId?: string) => void;
  onRemoveEnrolment: (id: string) => void;
}) {
  const session = sessions.find((s) => s.id === ctx.slot.sessionId);
  const enrolment = enrolments.find(
    (e) => e.childId === child.id && e.slotId === ctx.slot.id
  );

  const [startDate, setStartDate] = useState(
    enrolment?.startDate ?? toISODate(ctx.date)
  );
  const [endDate, setEndDate] = useState(
    enrolment?.endDate ?? ctx.slot.endDate ?? toISODate(addDays(ctx.date, 90))
  );

  if (!session) return null;

  const eligible = isAgeEligible(child, ctx.date, session);
  const enrolled = !!enrolment;
  const atCapacity = ctx.slot.childIds.length >= session.childLimit;

  const banner = enrolled
    ? { tone: 'green', text: `${child.firstName} is enrolled in this session.` }
    : eligible
    ? { tone: 'purple', text: `${child.firstName} is age-eligible for this session.` }
    : { tone: 'default', text: `${child.firstName} is outside this session's age range.` };

  const dur = session.durationHours * 60 + session.durationMinutes;
  const teacherNames = ctx.slot.teacherIds
    .map((id) => teachers.find((t) => t.id === id)?.name)
    .filter(Boolean)
    .join(', ');
  const enrolledNames = ctx.slot.childIds
    .map((id) => kids.find((k) => k.id === id))
    .filter((k): k is Child => !!k)
    .map((k) => `${k.firstName} ${k.lastName}`);
  const progress = progressForWeek(ctx.slot, ctx.date);
  const fillPct = Math.min(100, (ctx.slot.childIds.length / session.childLimit) * 100);

  return (
    <Modal
      open
      onClose={onClose}
      size="md"
      title={`${session.name} — ${DAY_LABELS[dayKeyForDate(ctx.date)]} ${ctx.slot.startTime}`}
      footer={
        <div className="flex items-center justify-between w-full">
          {enrolled ? (
            <Button
              variant="danger"
              onClick={() => onRemoveEnrolment(enrolment.id)}
            >
              Remove enrolment
            </Button>
          ) : (
            <span />
          )}
          <div className="flex items-center gap-2">
            <Button onClick={onClose}>Cancel</Button>
            <Button
              variant="purple"
              onClick={() => onEnrol(ctx.slot.id, startDate, endDate, enrolment?.id)}
            >
              {enrolled ? 'Update dates' : `Enrol ${child.firstName}`}
            </Button>
          </div>
        </div>
      }
    >
      <div className="space-y-4">
        <div
          className={[
            'rounded-md px-3 py-2 text-sm border',
            banner.tone === 'green'
              ? 'border-olive/40 bg-olive/10 text-olive'
              : banner.tone === 'purple'
              ? 'border-accent-purple/40 bg-accent-purple-soft text-accent-purple'
              : 'border-border bg-bg-elev text-text-muted',
          ].join(' ')}
        >
          {banner.text}
        </div>

        <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
          <Row label="Day & time">
            {DAY_LABELS[dayKeyForDate(ctx.date)]} · {ctx.slot.startTime}
          </Row>
          <Row label="Duration">
            {session.durationHours > 0 ? `${session.durationHours}hr ` : ''}
            {session.durationMinutes > 0 ? `${session.durationMinutes}min` : ''}
            {dur === 0 ? '—' : ''}
          </Row>
          <Row label="Teacher(s)">{teacherNames || '—'}</Row>
          <Row label="Course progress">
            M{progress.month} W{progress.week}
          </Row>
          <Row label="Age range">
            {session.ageFrom}–{session.ageTo} {session.ageUnit}
          </Row>
        </dl>

        <div>
          <div className="flex items-center justify-between text-xs text-text-muted mb-1">
            <span>
              Capacity {ctx.slot.childIds.length} / {session.childLimit}
            </span>
            {atCapacity && <span className="text-danger">At capacity</span>}
          </div>
          <div className="h-2 rounded-full bg-bg-elev overflow-hidden">
            <div
              className={`h-full ${atCapacity ? 'bg-danger' : 'bg-olive'}`}
              style={{ width: `${fillPct}%` }}
            />
          </div>
          {enrolledNames.length > 0 && (
            <div className="text-xs text-text-muted mt-2">
              <span className="font-semibold">Children enrolled:</span>{' '}
              {enrolledNames.join(', ')}
            </div>
          )}
        </div>

        {ctx.slot.notes && (
          <div className="text-sm">
            <div className="text-xs text-text-muted mb-1">Notes</div>
            <div className="rounded-md border border-border bg-bg-elev px-3 py-2">
              {ctx.slot.notes}
            </div>
          </div>
        )}

        <hr className="border-border" />

        <div>
          <div className="text-sm font-semibold mb-2">
            {enrolled ? 'Enrolment dates' : `Enrol ${child.firstName}`}
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Start date">
              <Input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
              />
            </Field>
            <Field label="End date">
              <Input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
              />
            </Field>
          </div>
          {atCapacity && !enrolled && (
            <div className="text-xs text-warn mt-2">
              ⚠️ This session is at capacity. Enrolling will add to the waitlist.
            </div>
          )}
          {!eligible && !enrolled && (
            <div className="text-xs text-text-muted mt-2">
              Enrolling outside the age range is allowed but discouraged.
            </div>
          )}
        </div>
      </div>
      {/* avoid unused warning */}
      <span className="hidden">{centre.id}</span>
    </Modal>
  );
}

function Row({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-text-muted">{label}</dt>
      <dd className="mt-0.5">{children}</dd>
    </div>
  );
}

function BillPayersSection({ child }: { child: Child }) {
  const { billPayerBalances } = useStore();
  const billPayers = child.contacts.filter((c) => c.isBillPayer);
  return (
    <div className="card p-5">
      <div className="flex items-center justify-between mb-3">
        <div className="text-base font-semibold">Linked bill payers</div>
        <Button>+ Add</Button>
      </div>
      {billPayers.length === 0 ? (
        <div className="text-sm text-text-dim">No bill payers linked.</div>
      ) : (
        <ul className="space-y-2">
          {billPayers.map((c) => {
            const balance = billPayerBalances.find((b) => b.contactId === c.id);
            const overdue = (balance?.balance ?? 0) > 0;
            return (
              <li
                key={c.id}
                className="flex items-center justify-between rounded-lg border border-border p-3"
              >
                <div className="flex items-center gap-3">
                  <span className="w-9 h-9 rounded-full inline-flex items-center justify-center font-semibold text-sm bg-accent-blue-soft text-accent-blue">
                    {initialsOf(c.name)}
                  </span>
                  <div>
                    <div className="font-semibold leading-tight">{c.name}</div>
                    <div className="text-xs text-text-muted">
                      {c.isMain ? 'Main bill payer' : 'Secondary'}
                    </div>
                  </div>
                </div>
                <div className="text-right">
                  <div
                    className={`font-semibold text-sm ${
                      overdue ? 'text-danger' : 'text-olive'
                    }`}
                  >
                    {overdue
                      ? `£${(balance?.balance ?? 0).toFixed(2)} owed`
                      : 'Cleared'}
                  </div>
                  <div className="text-[11px] text-text-muted">
                    {balance?.lastNote ?? '—'}
                  </div>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

const KIND_TONE: Record<string, 'olive' | 'gold' | 'danger'> = {
  Session: 'olive',
  Consumable: 'gold',
  'Late fee': 'danger',
};

function PurchasesSection({
  purchases,
  onAdd,
}: {
  child: Child;
  purchases: ReturnType<typeof useStore>['purchases'];
  onAdd: () => void;
}) {
  return (
    <div className="card p-5">
      <div className="flex items-center justify-between mb-3">
        <div className="text-base font-semibold">Recent</div>
        <Button variant="purple" onClick={onAdd}>
          + Add
        </Button>
      </div>
      {purchases.length === 0 ? (
        <div className="text-sm text-text-dim">No purchases yet.</div>
      ) : (
        <ul className="divide-y divide-border">
          {purchases.map((p) => (
            <li
              key={p.id}
              className="py-2.5 flex items-center justify-between gap-3"
            >
              <div className="flex items-center gap-2 min-w-0">
                <Badge tone={KIND_TONE[p.kind] ?? 'default'}>{p.kind}</Badge>
                <div className="min-w-0">
                  <div className="text-sm font-medium truncate">{p.name}</div>
                  <div className="text-[11px] text-text-muted">
                    {formatLongDate(fromISODate(p.date))}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <span className="text-sm font-semibold">
                  £{p.amount.toFixed(2)}
                </span>
                <Badge tone={p.paid ? 'green' : 'danger'}>
                  {p.paid ? 'Paid' : 'Unpaid'}
                </Badge>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

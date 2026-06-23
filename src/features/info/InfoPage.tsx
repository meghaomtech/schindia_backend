import { useMemo } from 'react';
import type { ComponentType, SVGProps } from 'react';
import { PageHeader } from '@/components/ui/PageHeader';
import { Badge } from '@/components/ui/Badge';
import { useStore } from '@/store/store';
import { paletteFor } from '@/lib/colors';
import {
  CentresIcon,
  ChildrenIcon,
  ClipboardIcon,
  DoorIcon,
  RolesIcon,
  SessionsIcon,
  TeacherIcon,
  UserIcon,
} from '@/components/ui/icons';

interface CentreRow {
  id: string;
  name: string;
  children: number;
  teachers: number;
  sessions: number;
  rooms: number;
  slots: number;
  roles: number;
  people: number;
}

export function InfoPage() {
  const { centres, sessions, slots, teachers, children: kids, enrolments, roles } =
    useStore();

  const rows: CentreRow[] = useMemo(() => {
    return centres.map((c) => {
      const centreSlots = slots.filter((s) => s.centreId === c.id);
      const teacherIds = new Set<string>();
      for (const s of centreSlots) for (const t of s.teacherIds) teacherIds.add(t);
      const centreRoles = roles.filter((r) => r.centreId === c.id);
      const totalPeople = centreRoles.reduce((n, r) => n + r.members.length, 0);
      return {
        id: c.id,
        name: c.name,
        children: kids.filter((k) => k.centreId === c.id).length,
        teachers: teacherIds.size,
        sessions: sessions.filter((s) => s.centreId === c.id).length,
        rooms: c.rooms.length,
        slots: centreSlots.length,
        roles: centreRoles.length,
        people: totalPeople,
      };
    });
  }, [centres, kids, sessions, slots, roles]);

  const totals = useMemo(
    () => ({
      centres: centres.length,
      children: kids.length,
      teachers: teachers.length,
      sessions: sessions.length,
      rooms: centres.reduce((n, c) => n + c.rooms.length, 0),
      enrolments: enrolments.length,
      roles: roles.length,
      people: roles.reduce((n, r) => n + r.members.length, 0),
    }),
    [centres, kids, teachers, sessions, roles, enrolments]
  );

  const sessionPopularity = useMemo(() => {
    const counts = new Map<string, number>();
    for (const e of enrolments) {
      const slot = slots.find((s) => s.id === e.slotId);
      if (!slot) continue;
      counts.set(slot.sessionId, (counts.get(slot.sessionId) ?? 0) + 1);
    }
    return sessions
      .map((s) => ({
        id: s.id,
        name: s.name,
        color: s.colorBg,
        count: counts.get(s.id) ?? 0,
      }))
      .sort((a, b) => b.count - a.count);
  }, [sessions, slots, enrolments]);

  const ageBuckets = useMemo(() => {
    const buckets = [
      { label: '0–1y', min: 0, max: 12 },
      { label: '1–2y', min: 12, max: 24 },
      { label: '2–3y', min: 24, max: 36 },
      { label: '3–4y', min: 36, max: 48 },
      { label: '4–5y', min: 48, max: 60 },
      { label: '5y+', min: 60, max: 1200 },
    ].map((b) => ({ ...b, count: 0 }));
    const today = new Date();
    for (const k of kids) {
      const dob = new Date(k.dateOfBirth);
      if (Number.isNaN(dob.getTime())) continue;
      const months =
        (today.getFullYear() - dob.getFullYear()) * 12 +
        (today.getMonth() - dob.getMonth());
      const b = buckets.find((x) => months >= x.min && months < x.max);
      if (b) b.count += 1;
    }
    return buckets;
  }, [kids]);

  const roleBreakdown = useMemo(() => {
    const map = new Map<string, { name: string; count: number }>();
    for (const r of roles) {
      const existing = map.get(r.name) ?? { name: r.name, count: 0 };
      existing.count += r.members.length;
      map.set(r.name, existing);
    }
    return [...map.values()].sort((a, b) => b.count - a.count);
  }, [roles]);

  return (
    <div className="space-y-5">
      <PageHeader
        title="Info"
        subtitle="A snapshot across all centres — children, teachers, sessions, roles and capacity."
      />

      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3">
        <Stat label="Centres" value={totals.centres} Icon={CentresIcon} tone="olive" />
        <Stat label="Children" value={totals.children} Icon={ChildrenIcon} tone="purple" />
        <Stat label="Teachers" value={totals.teachers} Icon={TeacherIcon} tone="blue" />
        <Stat label="Sessions" value={totals.sessions} Icon={SessionsIcon} tone="gold" />
        <Stat label="Rooms" value={totals.rooms} Icon={DoorIcon} tone="beige" />
        <Stat label="Enrolments" value={totals.enrolments} Icon={ClipboardIcon} tone="coral" />
        <Stat label="Roles" value={totals.roles} Icon={RolesIcon} tone="olive" />
        <Stat label="People" value={totals.people} Icon={UserIcon} tone="purple" />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
        <CentreBarChart rows={rows} />
        <RolesOverview roleBreakdown={roleBreakdown} rows={rows} />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
        <SessionPopularityList items={sessionPopularity} />
        <AgeDistribution buckets={ageBuckets} />
      </div>

      <CentreSummaryTable rows={rows} />
    </div>
  );
}

function Stat({
  label,
  value,
  Icon,
  tone,
}: {
  label: string;
  value: number;
  Icon: ComponentType<SVGProps<SVGSVGElement>>;
  tone: 'olive' | 'purple' | 'blue' | 'gold' | 'beige' | 'coral';
}) {
  const map: Record<typeof tone, string> = {
    olive: 'bg-olive/10 text-olive',
    purple: 'bg-accent-purple-soft text-accent-purple',
    blue: 'bg-accent-blue-soft text-accent-blue',
    gold: 'bg-gold-soft/40 text-brown',
    beige: 'bg-beige text-charcoal',
    coral: 'bg-accent-coral-soft text-accent-coral',
  };
  return (
    <div className="card p-4">
      <div
        className={[
          'w-8 h-8 rounded-lg inline-flex items-center justify-center mb-2',
          map[tone],
        ].join(' ')}
      >
        <Icon width={16} height={16} />
      </div>
      <div className="text-2xl font-semibold text-charcoal">{value}</div>
      <div className="text-[10px] text-text-muted uppercase tracking-wide">
        {label}
      </div>
    </div>
  );
}

function CentreBarChart({ rows }: { rows: CentreRow[] }) {
  const max = Math.max(1, ...rows.map((r) => Math.max(r.children, r.teachers)));
  return (
    <div className="card p-5">
      <div className="flex items-center justify-between mb-4">
        <div>
          <div className="text-base font-semibold text-charcoal">
            Children & teachers per centre
          </div>
          <div className="text-xs text-text-muted">
            Compare staffing and enrolment side by side.
          </div>
        </div>
        <div className="flex items-center gap-3 text-xs text-text-muted">
          <span className="flex items-center gap-1.5">
            <span
              className="inline-block w-3 h-3 rounded-sm"
              style={{ background: '#7c5fbf' }}
            />
            Children
          </span>
          <span className="flex items-center gap-1.5">
            <span
              className="inline-block w-3 h-3 rounded-sm"
              style={{ background: '#3b6db8' }}
            />
            Teachers
          </span>
        </div>
      </div>

      {rows.length === 0 ? (
        <div className="text-sm text-text-muted">No centres yet.</div>
      ) : (
        <ul className="space-y-3">
          {rows.map((r) => {
            const wKids = (r.children / max) * 100;
            const wTeach = (r.teachers / max) * 100;
            return (
              <li key={r.id}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium truncate">{r.name}</span>
                  <span className="text-xs text-text-muted">
                    {r.children} children · {r.teachers} teachers
                  </span>
                </div>
                <div className="space-y-1">
                  <div className="h-2.5 rounded-full bg-bg-elev overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all"
                      style={{ width: `${wKids}%`, background: '#7c5fbf' }}
                    />
                  </div>
                  <div className="h-2.5 rounded-full bg-bg-elev overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all"
                      style={{ width: `${wTeach}%`, background: '#3b6db8' }}
                    />
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

function RolesOverview({
  roleBreakdown,
  rows,
}: {
  roleBreakdown: { name: string; count: number }[];
  rows: CentreRow[];
}) {
  const totalPeople = rows.reduce((n, r) => n + r.people, 0);
  const max = Math.max(1, ...roleBreakdown.map((r) => r.count));

  const roleTone = (name: string) => {
    switch (name.toLowerCase()) {
      case 'manager': return '#5B6653';
      case 'teacher': return '#3b6db8';
      case 'parent': return '#B79C72';
      default: return '#7c5fbf';
    }
  };

  return (
    <div className="card p-5">
      <div className="mb-4">
        <div className="text-base font-semibold text-charcoal">
          Roles & people
        </div>
        <div className="text-xs text-text-muted">
          People assigned across all centres, grouped by role.
        </div>
      </div>

      {roleBreakdown.length === 0 ? (
        <div className="text-sm text-text-muted">No roles configured yet.</div>
      ) : (
        <div className="space-y-4">
          <div className="flex items-center gap-4">
            <div className="text-3xl font-bold text-charcoal">{totalPeople}</div>
            <div className="text-sm text-text-muted">total people across {rows.length} centres</div>
          </div>

          <ul className="space-y-2.5">
            {roleBreakdown.map((r) => {
              const color = roleTone(r.name);
              return (
                <li key={r.name}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="flex items-center gap-2 text-sm font-medium">
                      <span
                        className="inline-block w-2.5 h-2.5 rounded-full"
                        style={{ background: color }}
                      />
                      {r.name}
                    </span>
                    <span className="text-xs text-text-muted">
                      {r.count} {r.count === 1 ? 'person' : 'people'}
                    </span>
                  </div>
                  <div className="h-2 rounded-full bg-bg-elev overflow-hidden">
                    <div
                      className="h-full rounded-full"
                      style={{ width: `${(r.count / max) * 100}%`, background: color }}
                    />
                  </div>
                </li>
              );
            })}
          </ul>

          <div className="pt-2 border-t border-border">
            <div className="text-xs text-text-muted mb-2">Per centre</div>
            <div className="grid grid-cols-2 gap-2">
              {rows.map((r) => (
                <div key={r.id} className="flex items-center justify-between text-sm">
                  <span className="truncate">{r.name}</span>
                  <span className="text-text-muted text-xs">{r.people} people · {r.roles} roles</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function SessionPopularityList({
  items,
}: {
  items: { id: string; name: string; color: string; count: number }[];
}) {
  const max = Math.max(1, ...items.map((i) => i.count));
  return (
    <div className="card p-5">
      <div className="mb-4">
        <div className="text-base font-semibold text-charcoal">
          Session popularity
        </div>
        <div className="text-xs text-text-muted">
          Active enrolments per session.
        </div>
      </div>

      {items.length === 0 ? (
        <div className="text-sm text-text-muted">No sessions configured.</div>
      ) : (
        <ul className="space-y-2.5">
          {items.map((s) => {
            const palette = paletteFor(s.name);
            return (
              <li key={s.id}>
                <div className="flex items-center justify-between mb-1">
                  <span className="flex items-center gap-2 text-sm font-medium">
                    <span
                      className="inline-block w-2.5 h-2.5 rounded-full"
                      style={{ background: palette.bg }}
                    />
                    {s.name}
                  </span>
                  <span className="text-xs text-text-muted">
                    {s.count} {s.count === 1 ? 'enrolment' : 'enrolments'}
                  </span>
                </div>
                <div className="h-2 rounded-full bg-bg-elev overflow-hidden">
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${(s.count / max) * 100}%`,
                      background: palette.bg,
                    }}
                  />
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

function AgeDistribution({
  buckets,
}: {
  buckets: { label: string; count: number }[];
}) {
  const max = Math.max(1, ...buckets.map((b) => b.count));
  const chartHeight = 140;

  return (
    <div className="card p-5">
      <div className="mb-4">
        <div className="text-base font-semibold text-charcoal">
          Age distribution
        </div>
        <div className="text-xs text-text-muted">
          How children are spread across age groups.
        </div>
      </div>

      <div
        className="grid items-end gap-3"
        style={{
          gridTemplateColumns: `repeat(${buckets.length}, minmax(0, 1fr))`,
          height: chartHeight,
        }}
      >
        {buckets.map((b) => {
          const h = (b.count / max) * (chartHeight - 24);
          return (
            <div
              key={b.label}
              className="flex flex-col items-center justify-end h-full"
            >
              <div className="text-xs text-text-muted mb-1">{b.count}</div>
              <div
                className="w-full rounded-t-md bg-olive/80"
                style={{ height: Math.max(4, h) }}
                title={`${b.label}: ${b.count}`}
              />
            </div>
          );
        })}
      </div>
      <div
        className="grid gap-3 mt-2"
        style={{
          gridTemplateColumns: `repeat(${buckets.length}, minmax(0, 1fr))`,
        }}
      >
        {buckets.map((b) => (
          <div key={b.label} className="text-center text-xs text-text-muted">
            {b.label}
          </div>
        ))}
      </div>
    </div>
  );
}

function CentreSummaryTable({ rows }: { rows: CentreRow[] }) {
  return (
    <div className="card p-5">
      <div className="mb-3">
        <div className="text-base font-semibold text-charcoal">
          Centres at a glance
        </div>
        <div className="text-xs text-text-muted">
          Per-centre counts of rooms, sessions, slots, people and roles.
        </div>
      </div>

      {rows.length === 0 ? (
        <div className="text-sm text-text-muted">No centres yet.</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-text-muted uppercase tracking-wide border-b border-border">
                <th className="py-2 pr-3 font-medium">Centre</th>
                <th className="py-2 px-3 font-medium">Rooms</th>
                <th className="py-2 px-3 font-medium">Sessions</th>
                <th className="py-2 px-3 font-medium">Slots</th>
                <th className="py-2 px-3 font-medium">Children</th>
                <th className="py-2 px-3 font-medium">Roles</th>
                <th className="py-2 px-3 font-medium">People</th>
                <th className="py-2 pl-3 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} className="border-b border-border/60 last:border-0">
                  <td className="py-2 pr-3 font-medium">{r.name}</td>
                  <td className="py-2 px-3">{r.rooms}</td>
                  <td className="py-2 px-3">{r.sessions}</td>
                  <td className="py-2 px-3">{r.slots}</td>
                  <td className="py-2 px-3">{r.children}</td>
                  <td className="py-2 px-3">{r.roles}</td>
                  <td className="py-2 px-3">{r.people}</td>
                  <td className="py-2 pl-3">
                    {r.children === 0 && r.people === 0 ? (
                      <Badge tone="beige">Empty</Badge>
                    ) : r.slots === 0 ? (
                      <Badge tone="gold">No schedule</Badge>
                    ) : (
                      <Badge tone="olive">Active</Badge>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

import { useMemo } from 'react';
import { useStore } from '@/store/store';
import {
  addDays,
  fromISODate,
  formatLongDate,
  startOfWeek,
  toISODate,
} from '@/lib/dates';
import { progressForWeek, slotAppearsOnDate } from '@/lib/recurrence';
import type { Child, JourneyType } from '@/lib/types';

interface FeedItem {
  kind: 'session' | 'journey' | 'note' | 'system';
  date: string;
  title: string;
  subtitle: string;
}

const DOT_COLOUR: Record<FeedItem['kind'], string> = {
  session: '#16a34a',
  journey: '#7c5fbf',
  note: '#d4a017',
  system: '#9ca3af',
};

export function ActivityTab({ child }: { child: Child }) {
  const { centres, sessions, slots, journeyEntries, notes, teachers } = useStore();
  const centre = centres.find((c) => c.id === child.centreId);

  const stats = useMemo(() => {
    const today = new Date();
    const ws = startOfWeek(today);
    const days = Array.from({ length: 7 }, (_, i) => addDays(ws, i));

    const childSlots = slots.filter((s) => s.childIds.includes(child.id));
    const sessionsThisWeek = centre
      ? childSlots.reduce((acc, s) => {
          for (const d of days) {
            if (slotAppearsOnDate(s, d, centre)) acc += 1;
          }
          return acc;
        }, 0)
      : 0;

    let totalSessions = 0;
    if (centre) {
      for (const s of childSlots) {
        if (s.bookingType === 'one-off') {
          totalSessions += 1;
          continue;
        }
        if (!s.endDate) continue;
        const start = fromISODate(s.startDate);
        const end = fromISODate(s.endDate);
        for (
          let d = new Date(start);
          d <= end && d <= today;
          d.setDate(d.getDate() + 1)
        ) {
          if (slotAppearsOnDate(s, new Date(d), centre)) totalSessions += 1;
        }
      }
    }

    const journeyCount = journeyEntries.filter((e) => e.childId === child.id).length;

    let progress = '—';
    if (childSlots.length > 0) {
      const main = childSlots[0]!;
      const p = progressForWeek(main, today);
      progress = `M${p.month} W${p.week}`;
    }

    return { sessionsThisWeek, totalSessions, journeyCount, progress };
  }, [centre, slots, journeyEntries, child.id]);

  const feed = useMemo<FeedItem[]>(() => {
    const items: FeedItem[] = [];

    items.push({
      kind: 'system',
      date: child.startDate,
      title: 'Registered',
      subtitle: `Joined ${centre?.name ?? 'centre'}`,
    });

    for (const e of journeyEntries.filter((j) => j.childId === child.id)) {
      items.push({
        kind: 'journey',
        date: e.date,
        title: `${e.type}: ${truncate(e.text, 60)}`,
        subtitle: `Logged by ${e.staffName}`,
      });
    }

    for (const n of notes.filter((x) => x.childId === child.id)) {
      items.push({
        kind: 'note',
        date: n.date,
        title: 'Note added',
        subtitle: `${truncate(n.text, 60)} — ${n.staffName}`,
      });
    }

    if (centre) {
      const today = new Date();
      const lookback = addDays(today, -14);
      const childSlots = slots.filter((s) => s.childIds.includes(child.id));
      for (const s of childSlots) {
        for (
          let d = new Date(lookback);
          d <= today;
          d.setDate(d.getDate() + 1)
        ) {
          if (!slotAppearsOnDate(s, new Date(d), centre)) continue;
          const session = sessions.find((x) => x.id === s.sessionId);
          const teacher = teachers.find((t) => t.id === s.teacherIds[0]);
          items.push({
            kind: 'session',
            date: toISODate(new Date(d)),
            title: `Attended ${session?.name ?? 'Session'}`,
            subtitle: teacher ? `with ${teacher.name}` : 'session',
          });
        }
      }
    }

    return items.sort((a, b) => (a.date < b.date ? 1 : -1)).slice(0, 12);
  }, [child, centre, journeyEntries, notes, slots, sessions, teachers]);

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <StatCard label="Sessions this week" value={stats.sessionsThisWeek} />
        <StatCard label="Total sessions" value={stats.totalSessions} />
        <StatCard label="Journey entries" value={stats.journeyCount} />
        <StatCard label="Course progress" value={stats.progress} />
      </div>

      <div className="card p-5">
        <div className="text-sm font-semibold mb-3">Recent activity</div>
        {feed.length === 0 ? (
          <div className="text-sm text-text-dim">Nothing yet.</div>
        ) : (
          <ul className="relative">
            <span
              aria-hidden="true"
              className="absolute left-[7px] top-1.5 bottom-1.5 w-px bg-border"
            />
            {feed.map((it, i) => (
              <li key={i} className="relative pl-7 pb-4 last:pb-0">
                <span
                  className="absolute left-0 top-1.5 w-3.5 h-3.5 rounded-full border-2 border-bg-card"
                  style={{ background: DOT_COLOUR[it.kind] }}
                />
                <div className="text-sm font-semibold leading-tight">
                  {it.title}
                </div>
                <div className="text-xs text-text-muted mt-0.5">
                  {it.subtitle}
                </div>
                <div className="text-xs text-text-dim mt-0.5">
                  {formatLongDate(fromISODate(it.date))}
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded-xl bg-bg-tertiary/60 border border-border px-4 py-3">
      <div className="text-xs uppercase tracking-wide text-text-muted">{label}</div>
      <div className="text-2xl font-semibold mt-1">{value}</div>
    </div>
  );
}

function truncate(s: string, n: number): string {
  if (s.length <= n) return s;
  return s.slice(0, n).trim() + '…';
}

// kept for type completeness
export type { JourneyType };

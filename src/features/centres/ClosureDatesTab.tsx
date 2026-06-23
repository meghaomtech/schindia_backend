import { useEffect, useMemo, useState } from 'react';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { CheckIcon, CloseIcon } from '@/components/ui/icons';
import { useStore } from '@/store/store';
import {
  formatLongDate,
  fromISODate,
  getCalendarMonth,
  isSameDay,
  toISODate,
} from '@/lib/dates';
import type { Centre } from '@/lib/types';

const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
];

export function ClosureDatesTab({ centre }: { centre: Centre }) {
  const { updateCentre } = useStore();
  const today = new Date();
  const [year, setYear] = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth());

  const [draft, setDraft] = useState<string[]>(centre.closureDates);
  const [savedAt, setSavedAt] = useState<number | null>(null);

  useEffect(() => {
    setDraft(centre.closureDates);
    setSavedAt(null);
  }, [centre.id]);

  const draftSet = useMemo(() => new Set(draft), [draft]);
  const weeks = useMemo(() => getCalendarMonth(year, month), [year, month]);

  const dirty = useMemo(() => {
    if (draft.length !== centre.closureDates.length) return true;
    const a = [...draft].sort();
    const b = [...centre.closureDates].sort();
    return a.some((d, i) => d !== b[i]);
  }, [draft, centre.closureDates]);

  function toggleDate(d: Date) {
    const iso = toISODate(d);
    setSavedAt(null);
    setDraft((prev) =>
      prev.includes(iso) ? prev.filter((x) => x !== iso) : [...prev, iso]
    );
  }

  function removeDate(iso: string) {
    setSavedAt(null);
    setDraft((prev) => prev.filter((d) => d !== iso));
  }

  function shiftMonth(delta: number) {
    let m = month + delta;
    let y = year;
    if (m < 0) { m = 11; y -= 1; }
    if (m > 11) { m = 0; y += 1; }
    setMonth(m);
    setYear(y);
  }

  function save() {
    updateCentre(centre.id, { closureDates: [...draft].sort() });
    setSavedAt(Date.now());
  }

  function discard() {
    setDraft(centre.closureDates);
    setSavedAt(null);
  }

  return (
    <div className="space-y-5">
      <div className="grid lg:grid-cols-2 gap-6">
        <div>
          <div className="flex items-center justify-between mb-3">
            <Button variant="ghost" onClick={() => shiftMonth(-1)} aria-label="Previous month">
              ←
            </Button>
            <div className="font-semibold">
              {MONTH_NAMES[month]} {year}
            </div>
            <Button variant="ghost" onClick={() => shiftMonth(1)} aria-label="Next month">
              →
            </Button>
          </div>

          <div className="grid grid-cols-7 gap-1 text-center text-xs text-text-muted mb-1">
            {['Mon','Tue','Wed','Thu','Fri','Sat','Sun'].map((d) => (
              <div key={d} className="py-1">{d}</div>
            ))}
          </div>

          <div className="grid grid-cols-7 gap-1">
            {weeks.flat().map((d, i) => {
              const inMonth = d.getMonth() === month;
              const iso = toISODate(d);
              const isClosure = draftSet.has(iso);
              const isToday = isSameDay(d, today);
              return (
                <button
                  key={i}
                  type="button"
                  onClick={() => toggleDate(d)}
                  aria-pressed={isClosure}
                  aria-label={`${formatLongDate(d)}${isClosure ? ' (closure)' : ''}`}
                  className={[
                    'aspect-square rounded-md text-sm transition-colors',
                    inMonth ? '' : 'opacity-40',
                    isClosure
                      ? 'bg-danger text-white font-semibold'
                      : isToday
                        ? 'bg-olive/10 text-olive border border-olive'
                        : 'bg-bg-elev text-text hover:bg-beige',
                  ].join(' ')}
                >
                  {d.getDate()}
                </button>
              );
            })}
          </div>

          <div className="mt-3 text-xs text-text-muted">
            Click a date to toggle it as a closure day. Changes apply only after you save.
          </div>
        </div>

        <div>
          <div className="text-xs uppercase tracking-wide text-text-muted mb-2">
            Closure dates ({draft.length})
          </div>
          {draft.length === 0 ? (
            <div className="card p-6 border-dashed text-sm text-text-dim text-center">
              No closure dates yet. Click any date in the calendar to add one.
            </div>
          ) : (
            <ul className="space-y-2">
              {[...draft].sort().map((iso) => (
                <li
                  key={iso}
                  className="card p-3 flex items-center justify-between"
                >
                  <div className="flex items-center gap-2">
                    <Badge tone="danger">Closed</Badge>
                    <span className="text-sm font-medium">
                      {formatLongDate(fromISODate(iso))}
                    </span>
                  </div>
                  <Button
                    variant="ghost"
                    aria-label={`Remove closure ${iso}`}
                    onClick={() => removeDate(iso)}
                  >
                    <CloseIcon width={16} height={16} />
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      <div className="flex items-center gap-3 pt-2 border-t border-border">
        <Button variant="primary" onClick={save} disabled={!dirty}>
          Save closure dates
        </Button>
        {dirty && (
          <Button onClick={discard}>
            Discard changes
          </Button>
        )}
        {savedAt && !dirty && (
          <span className="text-sm text-olive flex items-center gap-1">
            <CheckIcon width={14} height={14} /> Saved
          </span>
        )}
        {dirty && (
          <span className="text-sm text-text-muted">Unsaved changes</span>
        )}
      </div>
    </div>
  );
}

import { useEffect, useState } from 'react';
import { Toggle } from '@/components/ui/Toggle';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { CheckIcon } from '@/components/ui/icons';
import { useStore } from '@/store/store';
import { DAY_KEYS } from '@/lib/dates';
import type { Centre, DayKey, OpeningTimes } from '@/lib/types';

const DAY_LABEL_LONG: Record<DayKey, string> = {
  mon: 'Monday',
  tue: 'Tuesday',
  wed: 'Wednesday',
  thu: 'Thursday',
  fri: 'Friday',
  sat: 'Saturday',
  sun: 'Sunday',
};

export function OpeningTimesTab({ centre }: { centre: Centre }) {
  const { updateCentre } = useStore();
  const [times, setTimes] = useState<OpeningTimes>(centre.openingTimes);
  const [savedAt, setSavedAt] = useState<number | null>(null);

  useEffect(() => {
    setTimes(centre.openingTimes);
    setSavedAt(null);
  }, [centre.id]);

  function setOpen(day: DayKey, open: boolean) {
    setTimes((t) => ({
      ...t,
      [day]: {
        ...t[day],
        open,
        opensAt: open && !t[day].opensAt ? '08:00' : t[day].opensAt,
        closesAt: open && !t[day].closesAt ? '17:00' : t[day].closesAt,
      },
    }));
  }

  function setTime(day: DayKey, key: 'opensAt' | 'closesAt', value: string) {
    setTimes((t) => ({ ...t, [day]: { ...t[day], [key]: value } }));
  }

  function save() {
    updateCentre(centre.id, { openingTimes: times });
    setSavedAt(Date.now());
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-text-muted">
        Set opening hours for each day. The schedule grid uses these times to render the
        weekly calendar.
      </p>

      <div className="card p-2 divide-y divide-border">
        {DAY_KEYS.map((day) => {
          const t = times[day];
          return (
            <div
              key={day}
              className="grid grid-cols-12 items-center gap-3 py-3 px-2"
            >
              <div className="col-span-3">
                <Toggle
                  checked={t.open}
                  onChange={(v) => setOpen(day, v)}
                  label={DAY_LABEL_LONG[day]}
                />
              </div>
              <div className="col-span-9 grid grid-cols-2 gap-3">
                <label className="flex items-center gap-2">
                  <span className="text-xs text-text-muted w-16">Opens at</span>
                  <Input
                    type="time"
                    value={t.opensAt}
                    disabled={!t.open}
                    onChange={(e) => setTime(day, 'opensAt', e.target.value)}
                    className="flex-1"
                  />
                </label>
                <label className="flex items-center gap-2">
                  <span className="text-xs text-text-muted w-16">Closes at</span>
                  <Input
                    type="time"
                    value={t.closesAt}
                    disabled={!t.open}
                    onChange={(e) => setTime(day, 'closesAt', e.target.value)}
                    className="flex-1"
                  />
                </label>
              </div>
            </div>
          );
        })}
      </div>

      <div className="flex items-center gap-3">
        <Button variant="primary" onClick={save}>
          Save opening times
        </Button>
        {savedAt && (
          <span className="text-sm text-olive flex items-center gap-1">
            <CheckIcon width={14} height={14} /> Saved
          </span>
        )}
      </div>
    </div>
  );
}

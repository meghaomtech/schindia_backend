import { useEffect, useMemo, useState } from 'react';
import { Field, Input, Select } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { useStore } from '@/store/store';
import { validateSession } from '@/lib/validation';
import { uid } from '@/lib/ids';
import { paletteFor } from '@/lib/colors';
import type { AgeUnit, Session, ValidationError } from '@/lib/types';

interface FormState {
  name: string;
  childLimit: number;
  ageFrom: number;
  ageTo: number;
  ageUnit: AgeUnit;
  durationHours: number;
  durationMinutes: number;
}

const emptyForm: FormState = {
  name: '',
  childLimit: 12,
  ageFrom: 0,
  ageTo: 5,
  ageUnit: 'years',
  durationHours: 1,
  durationMinutes: 30,
};

function fromSession(s: Session): FormState {
  return {
    name: s.name,
    childLimit: s.childLimit,
    ageFrom: s.ageFrom,
    ageTo: s.ageTo,
    ageUnit: s.ageUnit,
    durationHours: s.durationHours,
    durationMinutes: s.durationMinutes,
  };
}

function durationLabel(h: number, m: number): string {
  if (h > 0 && m > 0) return `${h}hr ${m}min`;
  if (h > 0) return `${h}hr`;
  return `${m}min`;
}

export function SessionEditor({
  session,
  onClose,
}: {
  session: Session | null;
  onClose: () => void;
}) {
  const { addSession, updateSession, deleteSession } = useStore();
  const [form, setForm] = useState<FormState>(() =>
    session ? fromSession(session) : emptyForm
  );
  const [errors, setErrors] = useState<ValidationError[]>([]);

  useEffect(() => {
    setForm(session ? fromSession(session) : emptyForm);
    setErrors([]);
  }, [session?.id]);

  const errMap = useMemo(() => {
    const m: Record<string, string> = {};
    for (const e of errors) m[e.field] = e.message;
    return m;
  }, [errors]);

  function save() {
    const errs = validateSession(form);
    setErrors(errs);
    if (errs.length > 0) return;

    const palette = paletteFor(form.name);
    if (session) {
      updateSession(session.id, {
        name: form.name.trim(),
        childLimit: form.childLimit,
        ageFrom: form.ageFrom,
        ageTo: form.ageTo,
        ageUnit: form.ageUnit,
        durationHours: form.durationHours,
        durationMinutes: form.durationMinutes,
      });
    } else {
      const s: Session = {
        id: uid('s'),
        name: form.name.trim(),
        childLimit: form.childLimit,
        ageFrom: form.ageFrom,
        ageTo: form.ageTo,
        ageUnit: form.ageUnit,
        durationHours: form.durationHours,
        durationMinutes: form.durationMinutes,
        colorBg: palette.bg,
        colorText: palette.text,
      };
      addSession(s);
    }
    onClose();
  }

  function remove() {
    if (!session) return;
    if (confirm(`Delete session "${session.name}"? This cannot be undone.`)) {
      deleteSession(session.id);
      onClose();
    }
  }

  return (
    <div className="card p-5 space-y-4">
      <div className="flex items-center justify-between">
        <div className="text-lg font-semibold">
          {session ? `Edit — ${session.name}` : 'New session'}
        </div>
        {session && (
          <Button variant="danger" onClick={remove}>
            Delete
          </Button>
        )}
      </div>

      <div className="grid grid-cols-2 gap-3">
        <Field label="Session name" required error={errMap.name}>
          <Input
            value={form.name}
            placeholder="e.g. Puppies, Bears"
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            invalid={!!errMap.name}
          />
        </Field>
        <Field label="Child limit" required error={errMap.childLimit}>
          <Input
            type="number"
            min={1}
            max={99}
            placeholder="e.g. 10"
            value={form.childLimit}
            onChange={(e) =>
              setForm({ ...form, childLimit: Number(e.target.value) || 0 })
            }
            invalid={!!errMap.childLimit}
          />
        </Field>
      </div>

      <div>
        <div className="label mb-1">
          Age range <span className="text-danger">*</span>
        </div>
        <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-2">
          <Field error={errMap.ageFrom}>
            <Input
              type="number"
              min={0}
              value={form.ageFrom}
              onChange={(e) =>
                setForm({ ...form, ageFrom: Number(e.target.value) || 0 })
              }
              invalid={!!errMap.ageFrom}
              placeholder="From"
              aria-label="Age from"
            />
          </Field>
          <span className="text-sm text-text-muted px-1">to</span>
          <Field error={errMap.ageTo}>
            <Input
              type="number"
              min={0}
              value={form.ageTo}
              onChange={(e) =>
                setForm({ ...form, ageTo: Number(e.target.value) || 0 })
              }
              invalid={!!errMap.ageTo}
              placeholder="To"
              aria-label="Age to"
            />
          </Field>
        </div>
        <div className="mt-2">
          <Field hint="Whether the age range above is in months or years">
            <Select
              value={form.ageUnit}
              onChange={(e) =>
                setForm({ ...form, ageUnit: e.target.value as AgeUnit })
              }
              aria-label="Age unit"
            >
              <option value="months">months</option>
              <option value="years">years</option>
            </Select>
          </Field>
        </div>
      </div>

      <div>
        <div className="label mb-1">
          Session duration <span className="text-danger">*</span>
        </div>
        <div className="grid grid-cols-2 gap-2">
          <Field>
            <Select
              value={form.durationHours}
              onChange={(e) =>
                setForm({ ...form, durationHours: Number(e.target.value) })
              }
              aria-label="Duration hours"
            >
              {Array.from({ length: 13 }, (_, i) => (
                <option key={i} value={i}>
                  {i} {i === 1 ? 'hour' : 'hours'}
                </option>
              ))}
            </Select>
          </Field>
          <Field>
            <Select
              value={form.durationMinutes}
              onChange={(e) =>
                setForm({ ...form, durationMinutes: Number(e.target.value) })
              }
              aria-label="Duration minutes"
            >
              {[0, 15, 30, 45].map((m) => (
                <option key={m} value={m}>
                  {m} minutes
                </option>
              ))}
            </Select>
          </Field>
        </div>
        <div className="mt-2 flex items-center gap-3">
          <span className="badge badge-olive">
            ⏱ {durationLabel(form.durationHours, form.durationMinutes)}
          </span>
          <span className="text-xs text-text-dim">Default is 1hr 30min</span>
        </div>
        {errMap.duration && (
          <div className="text-xs text-danger mt-1">{errMap.duration}</div>
        )}
      </div>

      <div className="flex items-center justify-between pt-2 border-t border-border">
        <Button onClick={onClose}>Cancel</Button>
        <Button variant="primary" onClick={save}>
          {session ? 'Save changes' : 'Create session'}
        </Button>
      </div>
    </div>
  );
}

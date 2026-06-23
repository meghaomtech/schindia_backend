import { useEffect, useMemo, useState } from 'react';
import { Field, Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { CheckIcon, CloseIcon } from '@/components/ui/icons';
import { useStore } from '@/store/store';
import { validateCentreDetails } from '@/lib/validation';
import { uid } from '@/lib/ids';
import type { Centre, Room, ValidationError } from '@/lib/types';

interface FormState {
  name: string;
  streetAddress: string;
  city: string;
  postcode: string;
  vatNumber: string;
  phone: string;
  email: string;
  managerName: string;
  rooms: Room[];
  bankAccountName: string;
  bankName: string;
  bankAccountNumber: string;
  bankSortCode: string;
  bankIfscCode: string;
  bankUpiId: string;
}

function fromCentre(c: Centre): FormState {
  return {
    name: c.name,
    streetAddress: c.streetAddress,
    city: c.city,
    postcode: c.postcode,
    vatNumber: c.vatNumber ?? '',
    phone: c.phone,
    email: c.email,
    managerName: c.managerName,
    rooms: c.rooms,
    bankAccountName: c.bankDetails?.accountName ?? '',
    bankName: c.bankDetails?.bankName ?? '',
    bankAccountNumber: c.bankDetails?.accountNumber ?? '',
    bankSortCode: c.bankDetails?.sortCode ?? '',
    bankIfscCode: c.bankDetails?.ifscCode ?? '',
    bankUpiId: c.bankDetails?.upiId ?? '',
  };
}

export function CentreDetailsTab({ centre }: { centre: Centre }) {
  const { updateCentre } = useStore();
  const [form, setForm] = useState<FormState>(() => fromCentre(centre));
  const [errors, setErrors] = useState<ValidationError[]>([]);
  const [savedAt, setSavedAt] = useState<number | null>(null);

  useEffect(() => {
    setForm(fromCentre(centre));
    setErrors([]);
    setSavedAt(null);
  }, [centre.id]);

  const errMap = useMemo(() => {
    const m: Record<string, string> = {};
    for (const e of errors) m[e.field] = e.message;
    return m;
  }, [errors]);

  function save() {
    const errs = validateCentreDetails(form);
    setErrors(errs);
    if (errs.length > 0) return;
    const hasBankDetails = form.bankAccountName.trim() || form.bankAccountNumber.trim();
    updateCentre(centre.id, {
      name: form.name.trim(),
      streetAddress: form.streetAddress.trim(),
      city: form.city.trim(),
      postcode: form.postcode.trim(),
      vatNumber: form.vatNumber.trim() || undefined,
      phone: form.phone.trim(),
      email: form.email.trim(),
      managerName: form.managerName.trim(),
      rooms: form.rooms.filter((r) => r.name.trim().length > 0),
      bankDetails: hasBankDetails
        ? {
            accountName: form.bankAccountName.trim(),
            bankName: form.bankName.trim(),
            accountNumber: form.bankAccountNumber.trim(),
            sortCode: form.bankSortCode.trim(),
            ifscCode: form.bankIfscCode.trim() || undefined,
            upiId: form.bankUpiId.trim() || undefined,
          }
        : undefined,
    });
    setSavedAt(Date.now());
  }

  function addRoom() {
    setForm((f) => ({ ...f, rooms: [...f.rooms, { id: uid('room'), name: '' }] }));
  }
  function updateRoom(id: string, name: string) {
    setForm((f) => ({
      ...f,
      rooms: f.rooms.map((r) => (r.id === id ? { ...r, name } : r)),
    }));
  }
  function removeRoom(id: string) {
    setForm((f) => ({ ...f, rooms: f.rooms.filter((r) => r.id !== id) }));
  }

  return (
    <div className="space-y-5">
      <div>
        <div className="text-xs uppercase tracking-wide text-text-muted mb-2">Centre identity</div>
        <Badge tone="beige">
          # System ID: <strong className="ml-1">{centre.systemId}</strong>{' '}
          <span className="text-text-dim ml-1">(read-only)</span>
        </Badge>
      </div>

      <Field label="Centre name" required error={errMap.name}>
        <Input
          value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
          invalid={!!errMap.name}
        />
      </Field>

      <div className="text-xs uppercase tracking-wide text-text-muted">Address</div>
      <Field label="Street address" required error={errMap.streetAddress}>
        <Input
          value={form.streetAddress}
          onChange={(e) => setForm({ ...form, streetAddress: e.target.value })}
          invalid={!!errMap.streetAddress}
        />
      </Field>
      <div className="grid grid-cols-2 gap-3">
        <Field label="City" required error={errMap.city}>
          <Input
            value={form.city}
            onChange={(e) => setForm({ ...form, city: e.target.value })}
            invalid={!!errMap.city}
          />
        </Field>
        <Field label="Postcode" required error={errMap.postcode}>
          <Input
            value={form.postcode}
            onChange={(e) => setForm({ ...form, postcode: e.target.value })}
            invalid={!!errMap.postcode}
          />
        </Field>
      </div>

      <div className="text-xs uppercase tracking-wide text-text-muted pt-2">Contact &amp; admin</div>
      <div className="grid grid-cols-2 gap-3">
        <Field
          label="VAT number"
          hint="Leave blank if not VAT registered"
          error={errMap.vatNumber}
        >
          <Input
            value={form.vatNumber}
            onChange={(e) => setForm({ ...form, vatNumber: e.target.value })}
          />
        </Field>
        <Field label="Phone number" required error={errMap.phone}>
          <Input
            value={form.phone}
            onChange={(e) => setForm({ ...form, phone: e.target.value })}
            invalid={!!errMap.phone}
          />
        </Field>
        <Field label="Email address" required error={errMap.email}>
          <Input
            type="email"
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
            invalid={!!errMap.email}
          />
        </Field>
        <Field label="Centre manager" required error={errMap.managerName}>
          <Input
            value={form.managerName}
            onChange={(e) => setForm({ ...form, managerName: e.target.value })}
            invalid={!!errMap.managerName}
          />
        </Field>
      </div>

      <div className="text-xs uppercase tracking-wide text-text-muted pt-2">
        Bank details
        <span className="normal-case text-text-dim ml-1">(shown on invoices)</span>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <Field label="Account holder name">
          <Input
            value={form.bankAccountName}
            onChange={(e) => setForm({ ...form, bankAccountName: e.target.value })}
            placeholder="e.g. Shichida India Pvt Ltd"
          />
        </Field>
        <Field label="Bank name">
          <Input
            value={form.bankName}
            onChange={(e) => setForm({ ...form, bankName: e.target.value })}
            placeholder="e.g. HDFC Bank"
          />
        </Field>
        <Field label="Account number">
          <Input
            value={form.bankAccountNumber}
            onChange={(e) => setForm({ ...form, bankAccountNumber: e.target.value })}
            placeholder="e.g. 1234567890"
          />
        </Field>
        <Field label="Sort code / Branch code">
          <Input
            value={form.bankSortCode}
            onChange={(e) => setForm({ ...form, bankSortCode: e.target.value })}
            placeholder="e.g. 12-34-56"
          />
        </Field>
        <Field label="IFSC code" hint="For Indian bank transfers">
          <Input
            value={form.bankIfscCode}
            onChange={(e) => setForm({ ...form, bankIfscCode: e.target.value })}
            placeholder="e.g. HDFC0001234"
          />
        </Field>
        <Field label="UPI ID" hint="Optional — for UPI payments">
          <Input
            value={form.bankUpiId}
            onChange={(e) => setForm({ ...form, bankUpiId: e.target.value })}
            placeholder="e.g. centre@upi"
          />
        </Field>
      </div>

      <div className="pt-2">
        <div className="text-xs uppercase tracking-wide text-text-muted mb-2">Rooms</div>
        <div className="space-y-2">
          {form.rooms.length === 0 && (
            <div className="text-sm text-text-dim italic">No rooms added yet.</div>
          )}
          {form.rooms.map((r) => (
            <div key={r.id} className="flex items-center gap-2">
              <Input
                value={r.name}
                placeholder="e.g. Babies, Toddlers, Pre-school"
                onChange={(e) => updateRoom(r.id, e.target.value)}
              />
              <Button
                variant="ghost"
                aria-label={`Remove room ${r.name || 'unnamed'}`}
                onClick={() => removeRoom(r.id)}
              >
                <CloseIcon width={16} height={16} />
              </Button>
            </div>
          ))}
        </div>
        <Button onClick={addRoom} className="w-full border-dashed mt-2">
          + Add another room
        </Button>
      </div>

      <div className="flex items-center gap-3 pt-2">
        <Button variant="primary" onClick={save}>
          Save changes
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

import { useMemo, useState } from 'react';
import { Modal } from '@/components/ui/Modal';
import { Button } from '@/components/ui/Button';
import { Field, Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import {
  CheckIcon,
  CloseIcon,
  MailIcon,
  MapPinIcon,
  PhoneIcon,
  ReceiptIcon,
  UserIcon,
} from '@/components/ui/icons';
import { useStore } from '@/store/store';
import { nextCentreSystemId, uid } from '@/lib/ids';
import { validateCentreDetails } from '@/lib/validation';
import type { Centre, OpeningTimes, Room, ValidationError } from '@/lib/types';

const defaultOpeningTimes: OpeningTimes = {
  mon: { open: true, opensAt: '07:30', closesAt: '18:00' },
  tue: { open: true, opensAt: '07:30', closesAt: '18:00' },
  wed: { open: true, opensAt: '07:30', closesAt: '18:00' },
  thu: { open: true, opensAt: '07:30', closesAt: '18:00' },
  fri: { open: true, opensAt: '07:30', closesAt: '17:30' },
  sat: { open: false, opensAt: '', closesAt: '' },
  sun: { open: false, opensAt: '', closesAt: '' },
};

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

const emptyForm = (): FormState => ({
  name: '',
  streetAddress: '',
  city: '',
  postcode: '',
  vatNumber: '',
  phone: '',
  email: '',
  managerName: '',
  rooms: [],
  bankAccountName: '',
  bankName: '',
  bankAccountNumber: '',
  bankSortCode: '',
  bankIfscCode: '',
  bankUpiId: '',
});

export function AddCentreModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { addCentre } = useStore();
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [systemId] = useState(() => nextCentreSystemId());
  const [form, setForm] = useState<FormState>(emptyForm);
  const [errors, setErrors] = useState<ValidationError[]>([]);

  const errMap = useMemo(() => {
    const m: Record<string, string> = {};
    for (const e of errors) m[e.field] = e.message;
    return m;
  }, [errors]);

  function reset() {
    setStep(1);
    setForm(emptyForm());
    setErrors([]);
  }

  function handleClose() {
    reset();
    onClose();
  }

  function continueFromStep1() {
    const errs = validateCentreDetails(form);
    setErrors(errs);
    if (errs.length === 0) setStep(2);
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

  function finalize() {
    const hasBankDetails = form.bankAccountName.trim() || form.bankAccountNumber.trim();
    const c: Centre = {
      id: uid('c'),
      systemId,
      name: form.name.trim(),
      streetAddress: form.streetAddress.trim(),
      city: form.city.trim(),
      postcode: form.postcode.trim(),
      vatNumber: form.vatNumber.trim() || undefined,
      phone: form.phone.trim(),
      email: form.email.trim(),
      managerName: form.managerName.trim(),
      rooms: form.rooms.filter((r) => r.name.trim().length > 0),
      closureDates: [],
      openingTimes: defaultOpeningTimes,
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
    };
    addCentre(c);
    handleClose();
  }

  const progressPct = (step / 3) * 100;

  return (
    <Modal
      open={open}
      onClose={handleClose}
      size="md"
      topStrip={
        <div className="h-1 bg-bg-elev">
          <div
            className="h-full bg-olive transition-all"
            style={{ width: `${progressPct}%` }}
          />
        </div>
      }
      title={
        <div className="flex items-center gap-3">
          <span>Add new centre</span>
        </div>
      }
      footer={
        <div className="flex items-center justify-between w-full">
          {step > 1 ? (
            <Button onClick={() => setStep((step - 1) as 1 | 2)}>← Back</Button>
          ) : (
            <Button onClick={handleClose}>Cancel</Button>
          )}
          {step === 1 && (
            <Button variant="primary" onClick={continueFromStep1}>
              Continue →
            </Button>
          )}
          {step === 2 && (
            <Button variant="primary" onClick={() => setStep(3)}>
              Continue →
            </Button>
          )}
          {step === 3 && (
            <Button variant="primary" onClick={finalize}>
              <CheckIcon width={16} height={16} className="mr-1" /> Create centre
            </Button>
          )}
        </div>
      }
    >
      <Stepper step={step} />

      {step === 1 && (
        <div className="space-y-4">
          <div className="text-xs uppercase tracking-wide text-text-muted">Centre identity</div>
          <Badge tone="beige">
            # System ID: <strong className="ml-1">{systemId}</strong>{' '}
            <span className="text-text-dim ml-1">(auto-generated)</span>
          </Badge>

          <Field label="Centre name" required error={errMap.name}>
            <Input
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              invalid={!!errMap.name}
            />
          </Field>

          <div className="text-xs uppercase tracking-wide text-text-muted pt-2">Address</div>
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

          <div className="text-xs uppercase tracking-wide text-text-muted pt-2">
            Contact &amp; admin
          </div>
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
        </div>
      )}

      {step === 2 && (
        <div className="space-y-4">
          <div className="text-xs uppercase tracking-wide text-text-muted">
            Rooms in this centre
          </div>
          <p className="text-sm text-text-muted">
            Add the room names for this centre. You can edit these later.
          </p>
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
          <Button onClick={addRoom} className="w-full border-dashed">
            + Add another room
          </Button>
        </div>
      )}

      {step === 3 && (
        <div className="space-y-4">
          <div className="text-xs uppercase tracking-wide text-text-muted">Review centre details</div>
          <div className="card p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-olive/15 text-olive flex items-center justify-center font-bold">
                {form.name?.[0]?.toUpperCase() ?? '?'}
              </div>
              <div>
                <div className="font-semibold">{form.name || '(unnamed)'}</div>
                <div className="text-xs text-text-dim font-mono">{systemId}</div>
              </div>
            </div>
            <div className="mt-3 text-sm divide-y divide-border">
              <div className="py-1.5 flex items-center gap-2">
                <MapPinIcon width={14} height={14} className="text-text-muted shrink-0" />
                <span>{form.streetAddress}, {form.city}, {form.postcode}</span>
              </div>
              <div className="py-1.5 flex items-center gap-2">
                <PhoneIcon width={14} height={14} className="text-text-muted shrink-0" />
                <span>{form.phone}</span>
              </div>
              <div className="py-1.5 flex items-center gap-2">
                <MailIcon width={14} height={14} className="text-text-muted shrink-0" />
                <span>{form.email}</span>
              </div>
              <div className="py-1.5 flex items-center gap-2">
                <UserIcon width={14} height={14} className="text-text-muted shrink-0" />
                <span>{form.managerName}</span>
              </div>
              {form.vatNumber && (
                <div className="py-1.5 flex items-center gap-2">
                  <ReceiptIcon width={14} height={14} className="text-text-muted shrink-0" />
                  <span>VAT {form.vatNumber}</span>
                </div>
              )}
            </div>
          </div>
          {(form.bankAccountName || form.bankAccountNumber) && (
            <div>
              <div className="text-xs uppercase tracking-wide text-text-muted mb-2">
                Bank details (printed on invoices)
              </div>
              <div className="card p-3 text-sm space-y-1 bg-beige/30">
                {form.bankAccountName && (
                  <div><span className="text-text-muted">Account name:</span> {form.bankAccountName}</div>
                )}
                {form.bankName && (
                  <div><span className="text-text-muted">Bank:</span> {form.bankName}</div>
                )}
                {form.bankAccountNumber && (
                  <div><span className="text-text-muted">Account no:</span> {form.bankAccountNumber}</div>
                )}
                {form.bankSortCode && (
                  <div><span className="text-text-muted">Sort/Branch code:</span> {form.bankSortCode}</div>
                )}
                {form.bankIfscCode && (
                  <div><span className="text-text-muted">IFSC:</span> {form.bankIfscCode}</div>
                )}
                {form.bankUpiId && (
                  <div><span className="text-text-muted">UPI:</span> {form.bankUpiId}</div>
                )}
              </div>
            </div>
          )}
          <div>
            <div className="text-xs uppercase tracking-wide text-text-muted mb-2">
              Rooms ({form.rooms.length})
            </div>
            {form.rooms.length === 0 ? (
              <div className="text-sm text-text-dim">No rooms added</div>
            ) : (
              <div className="flex flex-wrap gap-1.5">
                {form.rooms.map((r) => (
                  <Badge key={r.id} tone="beige">
                    {r.name || '(unnamed)'}
                  </Badge>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </Modal>
  );
}

function Stepper({ step }: { step: 1 | 2 | 3 }) {
  const labels = ['Centre details', 'Rooms', 'Review'] as const;
  return (
    <div className="flex items-center gap-3 mb-5">
      {labels.map((label, i) => {
        const idx = (i + 1) as 1 | 2 | 3;
        const done = idx < step;
        const active = idx === step;
        return (
          <div key={label} className="flex items-center gap-2">
            <span
              className={[
                'w-5 h-5 rounded-full text-[11px] inline-flex items-center justify-center font-semibold',
                done
                  ? 'bg-olive text-white'
                  : active
                    ? 'bg-olive/20 text-olive border border-olive'
                    : 'bg-bg-elev text-text-dim border border-border',
              ].join(' ')}
            >
              {done ? <CheckIcon width={12} height={12} /> : idx}
            </span>
            <span
              className={[
                'text-sm',
                done ? 'text-olive' : active ? 'text-olive font-medium' : 'text-text-dim',
              ].join(' ')}
            >
              {label}
            </span>
            {i < labels.length - 1 && <span className="text-text-dim mx-1">·</span>}
          </div>
        );
      })}
    </div>
  );
}

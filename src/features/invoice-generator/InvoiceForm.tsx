import { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { Field, Input } from '@/components/ui/Input';
import { TrashIcon } from '@/components/ui/icons';
import type {
  InvoiceFormData,
  ExtraLineItem,
  SavedCenter,
} from './invoiceGeneratorTypes';

const CENTERS_KEY = 'shichida_saved_centers_v2';
const INV_COUNTER_KEY = 'shichida_inv_counter_v2';

const COMPANY_GST = '06AAKCB5662Q1Z0';

function loadSavedCenters(): SavedCenter[] {
  try {
    return JSON.parse(localStorage.getItem(CENTERS_KEY) ?? '[]');
  } catch {
    return [];
  }
}

export function nextInvoiceNum(): string {
  const yr = String(new Date().getFullYear()).slice(-2);
  const count = parseInt(localStorage.getItem(INV_COUNTER_KEY) ?? '0', 10) + 1;
  localStorage.setItem(INV_COUNTER_KEY, String(count));
  return `BA${yr}${String(count).padStart(4, '0')}`;
}

function uid(): string {
  return crypto.randomUUID();
}

export function newExtraItem(): ExtraLineItem {
  return { id: uid(), description: '', quantity: 1, amount: 0 };
}

export function defaultSession() {
  return { start: '', end: '', amount: 0 };
}

type FormErrors = Partial<Record<string, string>>;

export function InvoiceForm({
  data,
  onChange,
  onGenerate,
}: {
  data: InvoiceFormData;
  onChange: (d: InvoiceFormData) => void;
  onGenerate: () => void;
}) {
  const [savedCenters, setSavedCenters] = useState<SavedCenter[]>(loadSavedCenters);
  const [errors, setErrors] = useState<FormErrors>({});

  function set<K extends keyof InvoiceFormData>(key: K, value: InvoiceFormData[K]) {
    onChange({ ...data, [key]: value });
    if (errors[key]) setErrors((e) => ({ ...e, [key]: undefined }));
  }

  function saveCenter() {
    if (!data.centerCode.trim()) return;
    const existing = savedCenters.find((c) => c.centerCode === data.centerCode);
    let updated: SavedCenter[];
    if (existing) {
      updated = savedCenters.map((c) =>
        c.centerCode === data.centerCode
          ? { ...c, bankName: data.bankName, accountNumber: data.accountNumber, ifscCode: data.ifscCode, gstNumber: data.gstNumber }
          : c
      );
    } else {
      updated = [...savedCenters, {
        id: uid(),
        centerCode: data.centerCode,
        bankName: data.bankName,
        accountNumber: data.accountNumber,
        ifscCode: data.ifscCode,
        gstNumber: data.gstNumber,
      }];
    }
    localStorage.setItem(CENTERS_KEY, JSON.stringify(updated));
    setSavedCenters(updated);
  }

  function loadCenter(centerCode: string) {
    const c = savedCenters.find((x) => x.centerCode === centerCode);
    if (!c) return;
    onChange({ ...data, centerCode: c.centerCode, bankName: c.bankName, accountNumber: c.accountNumber, ifscCode: c.ifscCode, gstNumber: c.gstNumber });
  }

  function deleteCenter(id: string) {
    const updated = savedCenters.filter((c) => c.id !== id);
    localStorage.setItem(CENTERS_KEY, JSON.stringify(updated));
    setSavedCenters(updated);
  }

  function updateExtra(id: string, patch: Partial<ExtraLineItem>) {
    set('extraItems', data.extraItems.map((e) => (e.id === id ? { ...e, ...patch } : e)));
  }

  function removeExtra(id: string) {
    set('extraItems', data.extraItems.filter((e) => e.id !== id));
  }

  function validate(): boolean {
    const errs: FormErrors = {};
    if (!data.centerCode.trim()) errs.centerCode = 'Required';
    if (!data.studentName.trim()) errs.studentName = 'Required';
    if (!data.parentName.trim()) errs.parentName = 'Required';
    if (!data.invoiceNumber.trim()) errs.invoiceNumber = 'Required';
    if (!data.invoiceDate) errs.invoiceDate = 'Required';
    if (!data.dueDate) errs.dueDate = 'Required';
    if (!data.sessionFeeStart || !data.sessionFeeEnd) errs.sessionPeriod = 'Session period is required';
    if (!data.sessionFeeAmount) errs.sessionFeeAmount = 'Required';
    setErrors(errs);
    return Object.keys(errs).length === 0;
  }

  return (
    <div className="max-w-2xl mx-auto p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-charcoal">Invoice Generator</h1>
        <p className="text-sm text-text-muted mt-1">
          Shichida India — Brain Astra Pvt Ltd
        </p>
      </div>

      {/* Center / Payment Details */}
      <section className="card p-5 space-y-4">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <h2 className="font-semibold">Center & Payment Details</h2>
          <div className="flex items-center gap-2 flex-wrap">
            {savedCenters.length > 0 && (
              <div className="flex items-center gap-1">
                <select
                  className="input h-8 py-0 text-xs w-44"
                  defaultValue=""
                  onChange={(e) => { if (e.target.value) loadCenter(e.target.value); }}
                >
                  <option value="">Load saved center…</option>
                  {savedCenters.map((c) => (
                    <option key={c.id} value={c.centerCode}>{c.centerCode}</option>
                  ))}
                </select>
                <button
                  type="button"
                  title="Delete this saved center"
                  className="h-8 w-8 inline-flex items-center justify-center rounded-md text-text-muted hover:text-danger hover:bg-danger/10"
                  onClick={() => {
                    const sel = document.querySelector<HTMLSelectElement>('.center-sel-v2');
                    const found = savedCenters.find((c) => c.centerCode === sel?.value);
                    if (found) deleteCenter(found.id);
                  }}
                >
                  <TrashIcon width={14} height={14} />
                </button>
              </div>
            )}
            <Button onClick={saveCenter} className="h-8 py-0 text-xs">
              Save center
            </Button>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <Field label="Center Code" required error={errors.centerCode}>
            <Input
              value={data.centerCode}
              onChange={(e) => set('centerCode', e.target.value.toUpperCase())}
              invalid={!!errors.centerCode}
              placeholder="GGN_SEC50"
            />
          </Field>
          <Field label="GST Number">
            <Input
              value={data.gstNumber}
              onChange={(e) => set('gstNumber', e.target.value)}
              placeholder={COMPANY_GST}
            />
          </Field>
          <Field label="Bank Name">
            <Input
              value={data.bankName}
              onChange={(e) => set('bankName', e.target.value)}
              placeholder="IDFC Bank"
            />
          </Field>
          <Field label="Account Number">
            <Input
              value={data.accountNumber}
              onChange={(e) => set('accountNumber', e.target.value)}
              placeholder="10092938193"
            />
          </Field>
          <Field label="IFSC Code" hint="Used in Payment Details section">
            <Input
              value={data.ifscCode}
              onChange={(e) => set('ifscCode', e.target.value)}
              placeholder="IDFB0020141"
            />
          </Field>
        </div>
      </section>

      {/* Student Details */}
      <section className="card p-5 space-y-4">
        <h2 className="font-semibold">Student Details</h2>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Student Name" required error={errors.studentName}>
            <Input
              value={data.studentName}
              onChange={(e) => set('studentName', e.target.value)}
              invalid={!!errors.studentName}
              placeholder="Testing 1"
            />
          </Field>
          <Field label="Parent / Guardian" required error={errors.parentName}>
            <Input
              value={data.parentName}
              onChange={(e) => set('parentName', e.target.value)}
              invalid={!!errors.parentName}
              placeholder="Brain Astra"
            />
          </Field>
          <Field label="City">
            <Input
              value={data.city}
              onChange={(e) => set('city', e.target.value)}
              placeholder="Gurgaon"
            />
          </Field>
          <Field label="Contact Number">
            <Input
              value={data.contact}
              onChange={(e) => set('contact', e.target.value)}
              placeholder="7900 9700"
            />
          </Field>
          <Field label="Email" hint="Invoice will be sent here">
            <Input
              type="email"
              value={data.email}
              onChange={(e) => set('email', e.target.value)}
              placeholder="parent@email.com"
            />
          </Field>
        </div>
      </section>

      {/* Invoice Meta */}
      <section className="card p-5 space-y-4">
        <h2 className="font-semibold">Invoice Details</h2>
        <div className="grid grid-cols-3 gap-3">
          <Field label="Invoice #" required error={errors.invoiceNumber}>
            <Input
              value={data.invoiceNumber}
              onChange={(e) => set('invoiceNumber', e.target.value)}
              invalid={!!errors.invoiceNumber}
            />
          </Field>
          <Field label="Date" required error={errors.invoiceDate}>
            <Input
              type="date"
              value={data.invoiceDate}
              onChange={(e) => set('invoiceDate', e.target.value)}
              invalid={!!errors.invoiceDate}
            />
          </Field>
          <Field label="Due Date" required error={errors.dueDate}>
            <Input
              type="date"
              value={data.dueDate}
              onChange={(e) => set('dueDate', e.target.value)}
              invalid={!!errors.dueDate}
            />
          </Field>
        </div>
      </section>

      {/* Registration Details */}
      <section className="card p-5 space-y-4">
        <h2 className="font-semibold">Registration Details</h2>

        {/* Registration Fee */}
        <div className="rounded-lg border border-border bg-cream/40 p-4 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Registration Fee</span>
            <span className="text-xs text-text-muted">Leave 0 to omit from invoice</span>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Amount (₹)">
              <Input
                type="number"
                min={0}
                step={1}
                value={data.registrationFee || ''}
                onChange={(e) => set('registrationFee', Number(e.target.value) || 0)}
                placeholder="8000"
              />
            </Field>
          </div>
        </div>

        {/* Session Fee */}
        <div className="rounded-lg border border-border bg-cream/40 p-4 space-y-3">
          <div className="text-sm font-medium">Session Fee</div>
          {errors.sessionPeriod && (
            <p className="text-xs text-danger">{errors.sessionPeriod}</p>
          )}
          <div className="grid grid-cols-3 gap-3">
            <Field label="Start Date" required>
              <Input
                type="date"
                value={data.sessionFeeStart}
                onChange={(e) => {
                  set('sessionFeeStart', e.target.value);
                  setErrors((err) => ({ ...err, sessionPeriod: undefined }));
                }}
                invalid={!!errors.sessionPeriod}
              />
            </Field>
            <Field label="End Date" required>
              <Input
                type="date"
                value={data.sessionFeeEnd}
                onChange={(e) => {
                  set('sessionFeeEnd', e.target.value);
                  setErrors((err) => ({ ...err, sessionPeriod: undefined }));
                }}
                invalid={!!errors.sessionPeriod}
              />
            </Field>
            <Field label="Amount (₹)" required error={errors.sessionFeeAmount}>
              <Input
                type="number"
                min={0}
                step={1}
                value={data.sessionFeeAmount || ''}
                onChange={(e) => set('sessionFeeAmount', Number(e.target.value) || 0)}
                invalid={!!errors.sessionFeeAmount}
                placeholder="44000"
              />
            </Field>
          </div>
        </div>

        {/* Extra items */}
        {data.extraItems.length > 0 && (
          <div className="space-y-2">
            <div className="grid grid-cols-[1fr_80px_140px_36px] gap-2 text-xs text-text-muted px-1">
              <div>Description</div>
              <div>Qty</div>
              <div>Amount (₹)</div>
              <div />
            </div>
            <ul className="space-y-2">
              {data.extraItems.map((item) => (
                <li
                  key={item.id}
                  className="grid grid-cols-[1fr_80px_140px_36px] gap-2 items-start"
                >
                  <Input
                    value={item.description}
                    onChange={(e) => updateExtra(item.id, { description: e.target.value })}
                    placeholder="Description"
                  />
                  <Input
                    type="number"
                    min={1}
                    step={1}
                    value={item.quantity}
                    onChange={(e) => updateExtra(item.id, { quantity: Number(e.target.value) || 1 })}
                  />
                  <Input
                    type="number"
                    min={0}
                    step={1}
                    value={item.amount || ''}
                    onChange={(e) => updateExtra(item.id, { amount: Number(e.target.value) || 0 })}
                    placeholder="0"
                  />
                  <button
                    type="button"
                    onClick={() => removeExtra(item.id)}
                    className="h-9 inline-flex items-center justify-center rounded-md text-text-muted hover:text-danger hover:bg-danger/10"
                  >
                    <TrashIcon width={16} height={16} />
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}

        <button
          type="button"
          onClick={() => set('extraItems', [...data.extraItems, newExtraItem()])}
          className="btn-dashed"
        >
          + Add extra line item
        </button>
      </section>

      <div className="flex justify-end pb-8">
        <Button variant="primary" onClick={() => { if (validate()) onGenerate(); }} className="px-6">
          Preview Invoice →
        </Button>
      </div>
    </div>
  );
}

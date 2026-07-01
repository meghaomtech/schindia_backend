import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/Button';
import { Field, Input } from '@/components/ui/Input';
import { TrashIcon } from '@/components/ui/icons';
import type {
  InvoiceFormData,
  ExtraLineItem,
  SavedCenter,
} from './invoiceGeneratorTypes';
import { saveCenterToCloud, listCentersFromCloud, deleteCenterFromCloud, isApiConfigured } from '@/lib/invoiceApi';

const CENTERS_KEY = 'shichida_saved_centers_v2';
const INV_COUNTER_KEY = 'shichida_inv_counter_v2';

function loadSavedCentersLocal(): SavedCenter[] {
  try {
    return JSON.parse(localStorage.getItem(CENTERS_KEY) ?? '[]');
  } catch {
    return [];
  }
}

function persistCentersLocal(centers: SavedCenter[]) {
  localStorage.setItem(CENTERS_KEY, JSON.stringify(centers));
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
  const [savedCenters, setSavedCenters] = useState<SavedCenter[]>(loadSavedCentersLocal);
  const [errors, setErrors] = useState<FormErrors>({});
  const [centerSaved, setCenterSaved] = useState(false);
  const [bankSaved, setBankSaved] = useState(false);

  // On mount: merge cloud centers into localStorage so latest profiles are available
  useEffect(() => {
    if (!isApiConfigured()) return;
    listCentersFromCloud().then((cloudCenters) => {
      if (!cloudCenters.length) return;
      const local = loadSavedCentersLocal();
      const merged = [...local];
      for (const cc of cloudCenters) {
        if (!merged.find((l) => l.centerCode === cc.centerCode)) merged.push(cc);
        else merged.splice(merged.findIndex((l) => l.centerCode === cc.centerCode), 1, cc);
      }
      persistCentersLocal(merged);
      setSavedCenters(merged);
    }).catch(() => { /* silently use localStorage if cloud is unavailable */ });
  }, []);

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
          ? {
              ...c,
              centerLocation: data.centerLocation,
              fullAddress: data.fullAddress,
              centerEmail: data.centerEmail,
              centerPhone: data.centerPhone,
              gstNumber: data.gstNumber,
              website: data.website,
              bankName: data.bankName,
              accountNumber: data.accountNumber,
              ifscCode: data.ifscCode,
              upiId: data.upiId,
            }
          : c
      );
    } else {
      updated = [...savedCenters, {
        id: uid(),
        centerCode: data.centerCode,
        centerLocation: data.centerLocation,
        fullAddress: data.fullAddress,
        centerEmail: data.centerEmail,
        centerPhone: data.centerPhone,
        gstNumber: data.gstNumber,
        website: data.website,
        bankName: data.bankName,
        accountNumber: data.accountNumber,
        ifscCode: data.ifscCode,
        upiId: data.upiId,
      }];
    }
    persistCentersLocal(updated);
    setSavedCenters(updated);
    setCenterSaved(true);
    setTimeout(() => setCenterSaved(false), 2000);
    // Sync to cloud (fire-and-forget — localStorage is the source of truth locally)
    const saved = updated.find((c) => c.centerCode === data.centerCode);
    if (saved) saveCenterToCloud(saved).catch(() => {});
  }

  function saveBankAccount() {
    if (!data.centerCode.trim()) return;
    saveCenter();
    setBankSaved(true);
    setTimeout(() => setBankSaved(false), 2000);
  }

  function loadCenter(centerCode: string) {
    const c = savedCenters.find((x) => x.centerCode === centerCode);
    if (!c) return;
    onChange({
      ...data,
      centerCode: c.centerCode,
      centerLocation: c.centerLocation,
      fullAddress: c.fullAddress,
      centerEmail: c.centerEmail,
      centerPhone: c.centerPhone,
      gstNumber: c.gstNumber,
      website: c.website,
      bankName: c.bankName,
      accountNumber: c.accountNumber,
      ifscCode: c.ifscCode,
      upiId: c.upiId,
    });
  }

  function deleteCenter(id: string) {
    const target = savedCenters.find((c) => c.id === id);
    const updated = savedCenters.filter((c) => c.id !== id);
    persistCentersLocal(updated);
    setSavedCenters(updated);
    if (target) deleteCenterFromCloud(target.centerCode).catch(() => {});
  }

  function updateExtra(id: string, patch: Partial<ExtraLineItem>) {
    set('extraItems', data.extraItems.map((e) => (e.id === id ? { ...e, ...patch } : e)));
  }

  function removeExtra(id: string) {
    set('extraItems', data.extraItems.filter((e) => e.id !== id));
  }

  function updateDeduction(id: string, patch: Partial<ExtraLineItem>) {
    set('deductions', data.deductions.map((e) => (e.id === id ? { ...e, ...patch } : e)));
  }

  function removeDeduction(id: string) {
    set('deductions', data.deductions.filter((e) => e.id !== id));
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

      {/* Center Details */}
      <section className="card p-5 space-y-4">
        <h2 className="font-semibold">Center Details</h2>
        <p className="text-sm text-orange-500 font-semibold">Shichida India™</p>

        {savedCenters.length > 0 && (
          <div className="flex items-center gap-2 flex-wrap">
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

        <div className="grid grid-cols-2 gap-3">
          <Field label="Center Code" error={errors.centerCode}>
            <Input
              value={data.centerCode}
              onChange={(e) => set('centerCode', e.target.value.toUpperCase())}
              invalid={!!errors.centerCode}
              placeholder="GGN_SEC50"
            />
          </Field>
          <Field label="Center Location">
            <Input
              value={data.centerLocation}
              onChange={(e) => set('centerLocation', e.target.value)}
              placeholder="e.g. Bengaluru, Mumbai, Delhi"
            />
          </Field>
          <Field label="Full Address">
            <Input
              value={data.fullAddress}
              onChange={(e) => set('fullAddress', e.target.value)}
              placeholder="e.g. 12 MG Road, Bengaluru - 560001"
            />
          </Field>
          <Field label="Email (optional)">
            <Input
              type="email"
              value={data.centerEmail}
              onChange={(e) => set('centerEmail', e.target.value)}
              placeholder="center@shichidaindia.com"
            />
          </Field>
          <Field label="Phone (optional)">
            <Input
              value={data.centerPhone}
              onChange={(e) => set('centerPhone', e.target.value)}
              placeholder="+91-XXXXX-XXXXX"
            />
          </Field>
          <Field label="GST Number (optional)">
            <Input
              value={data.gstNumber}
              onChange={(e) => set('gstNumber', e.target.value)}
              placeholder="22AAAAA0000A1Z5"
            />
          </Field>
        </div>

        <div className="flex items-center gap-3 pt-1">
          <Button type="button" variant="primary" onClick={saveCenter} className="text-sm">
            Save Center
          </Button>
          {centerSaved
            ? <span className="text-sm text-olive font-medium">✓ Saved!</span>
            : <span className="text-xs text-text-muted">Save for quick selection next time</span>
          }
        </div>
      </section>

      {/* Bank Details */}
      <section className="card p-5 space-y-4">
        <h2 className="font-semibold">Bank Details</h2>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Bank Name">
            <Input
              value={data.bankName}
              onChange={(e) => set('bankName', e.target.value)}
              placeholder="e.g. IDFC Bank"
            />
          </Field>
          <Field label="Account Number">
            <Input
              value={data.accountNumber}
              onChange={(e) => set('accountNumber', e.target.value)}
              placeholder="e.g. 10092938193"
            />
          </Field>
          <Field label="IFSC Code">
            <Input
              value={data.ifscCode}
              onChange={(e) => set('ifscCode', e.target.value)}
              placeholder="e.g. SBIN0001234"
            />
          </Field>
          <Field label="UPI ID (optional)">
            <Input
              value={data.upiId}
              onChange={(e) => set('upiId', e.target.value)}
              placeholder="center@upi"
            />
          </Field>
        </div>

        <div className="flex items-center gap-3 pt-1">
          <Button type="button" variant="primary" onClick={saveBankAccount} className="text-sm">
            Save Bank Account
          </Button>
          {bankSaved
            ? <span className="text-sm text-olive font-medium">✓ Saved!</span>
            : <span className="text-xs text-text-muted">Save for quick selection next time</span>
          }
        </div>
      </section>

      {/* Student Details */}
      <section className="card p-5 space-y-4">
        <h2 className="font-semibold">Student Details</h2>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Student Name" error={errors.studentName}>
            <Input
              value={data.studentName}
              onChange={(e) => set('studentName', e.target.value)}
              invalid={!!errors.studentName}
              placeholder="Testing 1"
            />
          </Field>
          <Field label="Parent / Guardian" error={errors.parentName}>
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

      {/* Invoice Details */}
      <section className="card p-5 space-y-4">
        <h2 className="font-semibold">Invoice Details</h2>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Invoice Number" error={errors.invoiceNumber}>
            <Input
              value={data.invoiceNumber}
              onChange={(e) => set('invoiceNumber', e.target.value)}
              invalid={!!errors.invoiceNumber}
              placeholder="e.g. INV-1001"
            />
          </Field>
          <Field label="Invoice Date" error={errors.invoiceDate}>
            <Input
              type="date"
              value={data.invoiceDate}
              onChange={(e) => set('invoiceDate', e.target.value)}
              invalid={!!errors.invoiceDate}
            />
          </Field>
          <Field label="Due Date" error={errors.dueDate}>
            <Input
              type="date"
              value={data.dueDate}
              onChange={(e) => set('dueDate', e.target.value)}
              invalid={!!errors.dueDate}
            />
          </Field>
          <Field label="GST %">
            <Input
              type="number"
              min={0}
              step={1}
              value={data.gstPercent || ''}
              onChange={(e) => set('gstPercent', Number(e.target.value) || 0)}
              placeholder="0"
            />
          </Field>
          <Field label="Debit Brought Forward (₹)">
            <Input
              type="number"
              min={0}
              step={1}
              value={data.debitBroughtForward || ''}
              onChange={(e) => set('debitBroughtForward', Number(e.target.value) || 0)}
              placeholder="0"
            />
          </Field>
        </div>
      </section>

      {/* Monthly Sessions */}
      <section className="card p-5 space-y-4">
        <h2 className="font-semibold">Monthly Sessions</h2>

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
            <Field label="Start Date">
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
            <Field label="End Date">
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
            <Field label="Amount (₹)" error={errors.sessionFeeAmount}>
              <Input
                type="number"
                min={0}
                step={1}
                value={data.sessionFeeAmount || ''}
                onChange={(e) => set('sessionFeeAmount', Math.round(Number(e.target.value)) || 0)}
                invalid={!!errors.sessionFeeAmount}
                placeholder="44000"
              />
            </Field>
          </div>
        </div>
      </section>

      {/* Extra Charges */}
      <section className="card p-5 space-y-4">
        <h2 className="font-semibold">Extra Charges</h2>

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
          + Add Extra Charge
        </button>
      </section>

      {/* Deductions / Credits */}
      <section className="card p-5 space-y-4">
        <h2 className="font-semibold">Deductions / Credits</h2>

        {data.deductions.length > 0 && (
          <div className="space-y-2">
            <div className="grid grid-cols-[1fr_80px_140px_36px] gap-2 text-xs text-text-muted px-1">
              <div>Description</div>
              <div>Qty</div>
              <div>Amount (₹)</div>
              <div />
            </div>
            <ul className="space-y-2">
              {data.deductions.map((item) => (
                <li
                  key={item.id}
                  className="grid grid-cols-[1fr_80px_140px_36px] gap-2 items-start"
                >
                  <Input
                    value={item.description}
                    onChange={(e) => updateDeduction(item.id, { description: e.target.value })}
                    placeholder="Description"
                  />
                  <Input
                    type="number"
                    min={1}
                    step={1}
                    value={item.quantity}
                    onChange={(e) => updateDeduction(item.id, { quantity: Number(e.target.value) || 1 })}
                  />
                  <Input
                    type="number"
                    min={0}
                    step={1}
                    value={item.amount || ''}
                    onChange={(e) => updateDeduction(item.id, { amount: Number(e.target.value) || 0 })}
                    placeholder="0"
                  />
                  <button
                    type="button"
                    onClick={() => removeDeduction(item.id)}
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
          onClick={() => set('deductions', [...data.deductions, newExtraItem()])}
          className="btn-dashed"
        >
          + Add Deduction
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

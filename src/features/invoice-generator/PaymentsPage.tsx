import { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { Field, Input, Select } from '@/components/ui/Input';
import { TrashIcon } from '@/components/ui/icons';
import { Modal } from '@/components/ui/Modal';
import { loadPayments, savePayment, deletePayment, updatePayment, type Payment } from './paymentStorage';
import { loadInvoiceHistory } from './invoiceLocalStorage';

function fmtDate(iso: string): string {
  if (!iso) return '—';
  const [y, m, d] = iso.split('-').map(Number);
  return `${String(d).padStart(2, '0')}/${String(m).padStart(2, '0')}/${y}`;
}

function formatINR(n: number): string {
  return `₹ ${n.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
}

function todayISO(): string {
  return new Date().toISOString().slice(0, 10);
}

const PAYMENT_MODES = [
  { value: 'upi', label: 'UPI' },
  { value: 'bank_transfer', label: 'Bank Transfer' },
  { value: 'cash', label: 'Cash' },
  { value: 'cheque', label: 'Cheque' },
  { value: 'other', label: 'Other' },
] as const;

interface PaymentForm {
  invoiceNumber: string;
  studentName: string;
  parentName: string;
  centerCode: string;
  amount: number;
  paymentDate: string;
  paymentMode: Payment['paymentMode'];
  referenceNumber: string;
  notes: string;
}

function defaultForm(): PaymentForm {
  return {
    invoiceNumber: '',
    studentName: '',
    parentName: '',
    centerCode: '',
    amount: 0,
    paymentDate: todayISO(),
    paymentMode: 'upi',
    referenceNumber: '',
    notes: '',
  };
}

export function PaymentsPage() {
  const [payments, setPayments] = useState<Payment[]>(loadPayments);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<PaymentForm>(defaultForm);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);

  const invoices = loadInvoiceHistory();

  function handleInvoiceSelect(invoiceNumber: string) {
    const inv = invoices.find((i) => i.invoiceNumber === invoiceNumber);
    if (inv) {
      setForm({
        ...form,
        invoiceNumber: inv.invoiceNumber,
        studentName: inv.studentName,
        parentName: inv.parentName,
        centerCode: inv.centerCode,
      });
    } else {
      setForm({ ...form, invoiceNumber });
    }
  }

  function validate(): boolean {
    const errs: Record<string, string> = {};
    if (!form.parentName.trim()) errs.parentName = 'Required';
    if (!form.amount || form.amount <= 0) errs.amount = 'Enter a valid amount';
    if (!form.paymentDate) errs.paymentDate = 'Required';
    setErrors(errs);
    return Object.keys(errs).length === 0;
  }

  function handleSave() {
    if (!validate()) return;
    if (editingId) {
      // Update existing payment
      updatePayment(editingId, {
        invoiceNumber: form.invoiceNumber,
        studentName: form.studentName,
        parentName: form.parentName,
        centerCode: form.centerCode,
        amount: form.amount,
        paymentDate: form.paymentDate,
        paymentMode: form.paymentMode,
        referenceNumber: form.referenceNumber,
        notes: form.notes,
      });
    } else {
      // Create new payment
      const payment: Payment = {
        id: Date.now().toString(36) + Math.random().toString(36).slice(2, 9),
        invoiceNumber: form.invoiceNumber,
        studentName: form.studentName,
        parentName: form.parentName,
        centerCode: form.centerCode,
        amount: form.amount,
        paymentDate: form.paymentDate,
        paymentMode: form.paymentMode,
        referenceNumber: form.referenceNumber,
        notes: form.notes,
        createdAt: new Date().toISOString(),
      };
      savePayment(payment);
    }
    setPayments(loadPayments());
    setForm(defaultForm());
    setShowForm(false);
    setEditingId(null);
  }

  function handleEdit(payment: Payment) {
    setForm({
      invoiceNumber: payment.invoiceNumber,
      studentName: payment.studentName,
      parentName: payment.parentName,
      centerCode: payment.centerCode,
      amount: payment.amount,
      paymentDate: payment.paymentDate,
      paymentMode: payment.paymentMode,
      referenceNumber: payment.referenceNumber,
      notes: payment.notes,
    });
    setEditingId(payment.id);
    setShowForm(true);
  }

  function handleCancel() {
    setShowForm(false);
    setEditingId(null);
    setForm(defaultForm());
  }

  function handleDelete(id: string) {
    deletePayment(id);
    setPayments(loadPayments());
    setConfirmDelete(null);
  }

  return (
    <div className="max-w-4xl mx-auto space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-charcoal">Payments</h1>
          <p className="text-sm text-text-muted mt-1">Record and track payments received from parents</p>
        </div>
        <Button variant="primary" onClick={() => { if (showForm) { handleCancel(); } else { setShowForm(true); } }}>
          {showForm ? 'Cancel' : '+ Record Payment'}
        </Button>
      </div>

      {/* Payment Form */}
      {showForm && (
        <section className="card p-5 space-y-4">
          <h2 className="font-semibold">{editingId ? 'Edit Payment' : 'Record New Payment'}</h2>

          <div className="grid grid-cols-2 gap-3">
            <Field label="Link to Invoice (optional)">
              <Select
                value={form.invoiceNumber}
                onChange={(e) => handleInvoiceSelect(e.target.value)}
              >
                <option value="">— Select invoice —</option>
                {invoices.map((inv) => (
                  <option key={inv.invoiceNumber} value={inv.invoiceNumber}>
                    {inv.invoiceNumber} — {inv.studentName}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Payment Date" error={errors.paymentDate}>
              <Input
                type="date"
                value={form.paymentDate}
                onChange={(e) => setForm({ ...form, paymentDate: e.target.value })}
                invalid={!!errors.paymentDate}
              />
            </Field>
            <Field label="Student Name">
              <Input
                value={form.studentName}
                onChange={(e) => setForm({ ...form, studentName: e.target.value })}
                placeholder="Child's name"
              />
            </Field>
            <Field label="Parent / Guardian" error={errors.parentName}>
              <Input
                value={form.parentName}
                onChange={(e) => setForm({ ...form, parentName: e.target.value })}
                invalid={!!errors.parentName}
                placeholder="Parent name"
              />
            </Field>
            <Field label="Amount (₹)" error={errors.amount}>
              <Input
                type="number"
                min={0}
                step={1}
                value={form.amount || ''}
                onChange={(e) => setForm({ ...form, amount: Math.round(Number(e.target.value)) || 0 })}
                invalid={!!errors.amount}
                placeholder="e.g. 50000"
              />
            </Field>
            <Field label="Payment Mode">
              <Select
                value={form.paymentMode}
                onChange={(e) => setForm({ ...form, paymentMode: e.target.value as Payment['paymentMode'] })}
              >
                {PAYMENT_MODES.map((m) => (
                  <option key={m.value} value={m.value}>{m.label}</option>
                ))}
              </Select>
            </Field>
            <Field label="Reference / Transaction ID">
              <Input
                value={form.referenceNumber}
                onChange={(e) => setForm({ ...form, referenceNumber: e.target.value })}
                placeholder="e.g. UPI ref, cheque no."
              />
            </Field>
            <Field label="Center Code">
              <Input
                value={form.centerCode}
                onChange={(e) => setForm({ ...form, centerCode: e.target.value })}
                placeholder="e.g. GGN_SEC50"
              />
            </Field>
          </div>

          <Field label="Notes (optional)">
            <Input
              value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
              placeholder="Any additional info about this payment"
            />
          </Field>

          <div className="flex justify-end pt-2">
            <Button variant="primary" type="button" onClick={handleSave}>
              {editingId ? 'Update Payment' : 'Save Payment'}
            </Button>
          </div>
        </section>
      )}

      {/* Payments List */}
      {payments.length === 0 && !showForm ? (
        <div className="rounded-xl border border-border bg-cream/40 p-10 text-center text-text-muted text-sm">
          No payments recorded yet. Click "+ Record Payment" to add one.
        </div>
      ) : payments.length > 0 && (
        <div className="space-y-3">
          <p className="text-sm text-text-muted">
            {payments.length} payment{payments.length !== 1 ? 's' : ''} recorded
          </p>
          <div className="rounded-xl border border-border overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-border">
                  <th className="px-4 py-3 text-left font-semibold text-text-muted">Date</th>
                  <th className="px-4 py-3 text-left font-semibold text-text-muted">Student</th>
                  <th className="px-4 py-3 text-left font-semibold text-text-muted">Parent</th>
                  <th className="px-4 py-3 text-left font-semibold text-text-muted">Invoice</th>
                  <th className="px-4 py-3 text-left font-semibold text-text-muted">Mode</th>
                  <th className="px-4 py-3 text-left font-semibold text-text-muted">Reference</th>
                  <th className="px-4 py-3 text-right font-semibold text-text-muted">Amount</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody>
                {payments.map((p, i) => (
                  <tr
                    key={p.id}
                    className={`border-b border-border last:border-0 ${i % 2 === 0 ? 'bg-white' : 'bg-gray-50/50'}`}
                  >
                    <td className="px-4 py-3 text-text-muted">{fmtDate(p.paymentDate)}</td>
                    <td className="px-4 py-3">{p.studentName || '—'}</td>
                    <td className="px-4 py-3 text-text-muted">{p.parentName}</td>
                    <td className="px-4 py-3 font-mono text-xs text-[#1a5fa8]">
                      {p.invoiceNumber || '—'}
                    </td>
                    <td className="px-4 py-3 text-text-muted capitalize">
                      {p.paymentMode.replace('_', ' ')}
                    </td>
                    <td className="px-4 py-3 text-text-muted text-xs">
                      {p.referenceNumber || '—'}
                    </td>
                    <td className="px-4 py-3 text-right font-medium text-olive">
                      {formatINR(p.amount)}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          className="text-xs font-medium text-[#1a5fa8] hover:underline"
                          onClick={() => handleEdit(p)}
                        >
                          Edit
                        </button>
                        <button
                          className="h-7 w-7 inline-flex items-center justify-center rounded-md text-text-muted hover:text-danger hover:bg-danger/10"
                          title="Delete payment"
                          onClick={() => setConfirmDelete(p.id)}
                        >
                          <TrashIcon width={14} height={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      <Modal
        open={!!confirmDelete}
        onClose={() => setConfirmDelete(null)}
        title="Delete Payment"
        size="sm"
        footer={
          <>
            <Button variant="danger" onClick={() => { if (confirmDelete) handleDelete(confirmDelete); }}>
              Yes, Delete
            </Button>
            <Button onClick={() => setConfirmDelete(null)}>
              Cancel
            </Button>
          </>
        }
      >
        <p className="text-sm text-text-muted">
          Are you sure you want to delete this payment? This action cannot be undone.
        </p>
      </Modal>
    </div>
  );
}

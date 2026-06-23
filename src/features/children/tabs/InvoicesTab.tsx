import { useMemo, useState } from 'react';
import { Modal } from '@/components/ui/Modal';
import { Button } from '@/components/ui/Button';
import { Field, Input, Select } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { MailIcon, MobileIcon, TrashIcon } from '@/components/ui/icons';
import { useStore } from '@/store/store';
import { formatLongDate, fromISODate } from '@/lib/dates';
import { nextInvoiceNumber, uid } from '@/lib/ids';
import type {
  Child,
  Invoice,
  InvoiceItem,
  InvoiceStatus,
  PaymentTerm,
} from '@/lib/types';

const PAYMENT_TERMS: PaymentTerm[] = [
  'Monthly',
  'Quarterly',
  'Half-yearly',
  'Annually',
  'One-time',
];

function todayISO(): string {
  return new Date().toISOString().slice(0, 10);
}

function defaultDueDateFor(term: PaymentTerm, fromISO: string): string {
  const d = new Date(fromISO);
  if (Number.isNaN(d.getTime())) return fromISO;
  switch (term) {
    case 'Monthly':
      d.setDate(d.getDate() + 15);
      break;
    case 'Quarterly':
      d.setDate(d.getDate() + 30);
      break;
    case 'Half-yearly':
      d.setDate(d.getDate() + 45);
      break;
    case 'Annually':
      d.setDate(d.getDate() + 60);
      break;
    case 'One-time':
      d.setDate(d.getDate() + 7);
      break;
  }
  return d.toISOString().slice(0, 10);
}

function formatINR(n: number): string {
  return `₹${n.toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;
}

function statusTone(s: InvoiceStatus) {
  switch (s) {
    case 'Paid':
      return 'green' as const;
    case 'Sent':
      return 'blue' as const;
    case 'Overdue':
      return 'coral' as const;
    default:
      return 'beige' as const;
  }
}

export function InvoicesTab({ child }: { child: Child }) {
  const { invoices, deleteInvoice, updateInvoice } = useStore();
  const [open, setOpen] = useState(false);

  const items = useMemo(
    () =>
      invoices
        .filter((i) => i.childId === child.id)
        .sort((a, b) => (a.invoiceDate < b.invoiceDate ? 1 : -1)),
    [invoices, child.id]
  );

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-sm text-text-muted">
            Create invoices for fees, materials and ad-hoc charges. Sent invoices
            are emailed or SMSed to the bill-payer contacts on file.
          </div>
        </div>
        <Button variant="purple" onClick={() => setOpen(true)}>
          + Create invoice
        </Button>
      </div>

      {items.length === 0 ? (
        <div className="text-sm text-text-dim">No invoices yet.</div>
      ) : (
        <ul className="space-y-2">
          {items.map((inv) => {
            const subtotal = inv.items.reduce((n, i) => n + (i.amount || 0), 0);
            const tax = subtotal * (inv.taxRate / 100);
            const total = subtotal + tax;
            return (
              <li
                key={inv.id}
                className="rounded-xl border border-border bg-bg-tertiary/60 p-4"
              >
                <div className="flex items-start justify-between gap-3 mb-2">
                  <div>
                    <div className="font-mono text-xs text-text-muted">
                      {inv.number}
                    </div>
                    <div className="text-sm font-semibold">
                      {formatINR(total)} ·{' '}
                      <span className="text-text-muted font-normal">
                        Due {formatLongDate(fromISODate(inv.dueDate))}
                      </span>
                    </div>
                  </div>
                  <Badge tone={statusTone(inv.status)}>{inv.status}</Badge>
                </div>
                <ul className="space-y-0.5 text-sm">
                  {inv.items.map((it) => (
                    <li
                      key={it.id}
                      className="flex items-center justify-between"
                    >
                      <span className="text-text-muted">
                        {it.description || '(no description)'}
                      </span>
                      <span>{formatINR(it.amount)}</span>
                    </li>
                  ))}
                </ul>
                {inv.sentAt && inv.sentTo && inv.sentTo.length > 0 && (
                  <div className="text-xs text-text-dim mt-2 flex flex-wrap items-center gap-x-2 gap-y-1">
                    <span>Sent {formatLongDate(fromISODate(inv.sentAt))} via</span>
                    {inv.sentTo.map((s, i) => (
                      <span
                        key={`${s.channel}-${s.target}-${i}`}
                        className="inline-flex items-center gap-1"
                      >
                        {s.channel === 'email' ? (
                          <MailIcon width={11} height={11} />
                        ) : (
                          <MobileIcon width={11} height={11} />
                        )}
                        <span>{s.target}</span>
                      </span>
                    ))}
                  </div>
                )}
                <div className="mt-3 flex items-center justify-end gap-2">
                  {inv.status !== 'Paid' && (
                    <Button
                      onClick={() =>
                        updateInvoice(inv.id, { status: 'Paid' })
                      }
                    >
                      Mark paid
                    </Button>
                  )}
                  <Button
                    variant="ghost"
                    className="text-danger"
                    onClick={() => {
                      if (confirm(`Delete invoice ${inv.number}?`)) {
                        deleteInvoice(inv.id);
                      }
                    }}
                  >
                    Delete
                  </Button>
                </div>
              </li>
            );
          })}
        </ul>
      )}

      <CreateInvoiceModal
        open={open}
        onClose={() => setOpen(false)}
        child={child}
      />
    </div>
  );
}

function CreateInvoiceModal({
  open,
  onClose,
  child,
}: {
  open: boolean;
  onClose: () => void;
  child: Child;
}) {
  const { addInvoice, children: kids } = useStore();
  const [studentId, setStudentId] = useState(child.id);
  const [invoiceDate, setInvoiceDate] = useState(todayISO());
  const [paymentTerm, setPaymentTerm] = useState<PaymentTerm>('Monthly');
  const [dueDate, setDueDate] = useState(() =>
    defaultDueDateFor('Monthly', todayISO())
  );
  const [items, setItems] = useState<InvoiceItem[]>([
    { id: uid('inv-item'), description: '', amount: 0 },
  ]);
  const [taxRate, setTaxRate] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const targetChild = kids.find((c) => c.id === studentId) ?? child;
  const billPayers = targetChild.contacts.filter((c) => c.isBillPayer);

  const subtotal = items.reduce((n, i) => n + (Number(i.amount) || 0), 0);
  const tax = subtotal * (taxRate / 100);
  const total = subtotal + tax;

  function reset() {
    setStudentId(child.id);
    setInvoiceDate(todayISO());
    setPaymentTerm('Monthly');
    setDueDate(defaultDueDateFor('Monthly', todayISO()));
    setItems([{ id: uid('inv-item'), description: '', amount: 0 }]);
    setTaxRate(0);
    setError(null);
  }

  function close() {
    reset();
    onClose();
  }

  function updateItem(id: string, patch: Partial<InvoiceItem>) {
    setItems((arr) => arr.map((i) => (i.id === id ? { ...i, ...patch } : i)));
  }

  function removeItem(id: string) {
    setItems((arr) => (arr.length > 1 ? arr.filter((i) => i.id !== id) : arr));
  }

  function addItem() {
    setItems((arr) => [
      ...arr,
      { id: uid('inv-item'), description: '', amount: 0 },
    ]);
  }

  function onTermChange(t: PaymentTerm) {
    setPaymentTerm(t);
    setDueDate(defaultDueDateFor(t, invoiceDate));
  }

  function save(send: boolean) {
    const cleanedItems = items
      .map((i) => ({ ...i, amount: Number(i.amount) || 0 }))
      .filter((i) => i.description.trim() || i.amount > 0);
    if (cleanedItems.length === 0) {
      setError('Add at least one invoice item with an amount.');
      return;
    }
    if (!studentId) {
      setError('Select a student.');
      return;
    }
    if (!invoiceDate || !dueDate) {
      setError('Invoice date and due date are required.');
      return;
    }

    const sentTo = send
      ? billPayers.flatMap((c) => {
          const out: { channel: 'email' | 'sms'; target: string }[] = [];
          if (c.email) out.push({ channel: 'email', target: c.email });
          if (c.phone) out.push({ channel: 'sms', target: c.phone });
          return out;
        })
      : undefined;

    const inv: Invoice = {
      id: uid('inv'),
      number: nextInvoiceNumber(),
      childId: studentId,
      invoiceDate,
      dueDate,
      paymentTerm,
      items: cleanedItems,
      taxRate,
      status: send ? 'Sent' : 'Draft',
      sentAt: send ? new Date().toISOString().slice(0, 10) : undefined,
      sentTo,
    };
    addInvoice(inv);
    close();
  }

  return (
    <Modal
      open={open}
      onClose={close}
      size="lg"
      title="Create New Invoice"
      footer={
        <div className="flex items-center justify-between w-full gap-3">
          <div className="text-xs text-text-muted">
            {billPayers.length === 0
              ? 'No bill-payer contacts on file — invoice can be saved as draft.'
              : `Will be sent to ${billPayers
                  .map((c) => c.name || 'unnamed')
                  .join(', ')}.`}
          </div>
          <div className="flex items-center gap-2">
            <Button onClick={close}>Cancel</Button>
            <Button onClick={() => save(false)}>Save as draft</Button>
            <Button
              variant="purple"
              onClick={() => save(true)}
              disabled={billPayers.length === 0}
            >
              Send invoice
            </Button>
          </div>
        </div>
      }
    >
      <div className="space-y-5">
        <div className="grid grid-cols-2 gap-3">
          <Field label="Select student" required>
            <Select
              value={studentId}
              onChange={(e) => setStudentId(e.target.value)}
            >
              <option value="">Choose student...</option>
              {kids.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.firstName} {c.lastName} · {c.systemId}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Invoice date" required>
            <Input
              type="date"
              value={invoiceDate}
              onChange={(e) => {
                setInvoiceDate(e.target.value);
                setDueDate(defaultDueDateFor(paymentTerm, e.target.value));
              }}
            />
          </Field>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <Field label="Due date" required>
            <Input
              type="date"
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
            />
          </Field>
          <Field label="Payment term">
            <Select
              value={paymentTerm}
              onChange={(e) => onTermChange(e.target.value as PaymentTerm)}
            >
              {PAYMENT_TERMS.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </Select>
          </Field>
        </div>

        <div className="rounded-xl border border-border bg-cream/60 p-4">
          <div className="font-semibold mb-3">Invoice items</div>
          <div className="grid grid-cols-[1fr_160px_36px] gap-2 text-xs text-text-muted mb-1.5">
            <div>Description</div>
            <div>Amount (₹)</div>
            <div />
          </div>
          <ul className="space-y-2">
            {items.map((it) => (
              <li
                key={it.id}
                className="grid grid-cols-[1fr_160px_36px] gap-2 items-start"
              >
                <Input
                  placeholder="e.g., Quarterly fee"
                  value={it.description}
                  onChange={(e) =>
                    updateItem(it.id, { description: e.target.value })
                  }
                />
                <Input
                  type="number"
                  min={0}
                  step="0.01"
                  placeholder="0"
                  value={it.amount === 0 ? '' : it.amount}
                  onChange={(e) =>
                    updateItem(it.id, {
                      amount: e.target.value === '' ? 0 : Number(e.target.value),
                    })
                  }
                />
                <button
                  type="button"
                  onClick={() => removeItem(it.id)}
                  aria-label="Remove item"
                  className="h-9 inline-flex items-center justify-center rounded-md text-text-muted hover:text-danger hover:bg-danger/10"
                  disabled={items.length <= 1}
                >
                  <TrashIcon width={16} height={16} />
                </button>
              </li>
            ))}
          </ul>
          <button
            type="button"
            onClick={addItem}
            className="btn-dashed mt-3"
          >
            + Add item
          </button>
        </div>

        <div className="rounded-xl border border-border bg-beige/60 p-4 space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span>Subtotal</span>
            <span>{formatINR(subtotal)}</span>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="flex items-center gap-2">
              Tax
              <Input
                type="number"
                min={0}
                max={100}
                step="0.1"
                value={taxRate}
                onChange={(e) => setTaxRate(Number(e.target.value) || 0)}
                className="h-7 py-0 w-20"
                aria-label="Tax rate percent"
              />
              <span className="text-text-muted">%</span>
            </span>
            <span>{formatINR(tax)}</span>
          </div>
          <div className="border-t border-border-strong/40 pt-2 flex items-center justify-between font-semibold text-gold">
            <span>Total</span>
            <span>{formatINR(total)}</span>
          </div>
        </div>

        {error && (
          <div className="text-sm text-danger border border-danger/40 bg-danger/5 rounded-md px-3 py-2">
            {error}
          </div>
        )}
      </div>
    </Modal>
  );
}

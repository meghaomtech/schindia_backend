import { Button } from '@/components/ui/Button';
import type { InvoiceFormData } from './invoiceGeneratorTypes';

const COMPANY_LEGAL =
  'Shichida India licensed operating brand of Brain Astra Pvt Ltd. Company registration number CIN U72900KA2022PTC158571.';

function fmtDate(iso: string): string {
  if (!iso) return '';
  const [y, m, d] = iso.split('-').map(Number);
  return `${String(d).padStart(2, '0')}/${String(m).padStart(2, '0')}/${y}`;
}

function fmtPeriodDate(iso: string): string {
  if (!iso) return '';
  const [y, m, d] = iso.split('-').map(Number);
  return `${String(d).padStart(2, '0')}/${String(m).padStart(2, '0')}/${y}`;
}

function formatINR(n: number): string {
  return `₹ ${n.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
}

export function InvoicePreview({
  data,
  sent,
  sending = false,
  onBack,
  onSend,
  onCreateNew,
  onViewHistory,
}: {
  data: InvoiceFormData;
  sent: boolean;
  sending?: boolean;
  onBack: () => void;
  onSend: () => void;
  onCreateNew: () => void;
  onViewHistory?: () => void;
}) {
  const regFee = data.registrationFee ?? 0;
  const sessionFee = data.sessionFeeAmount ?? 0;
  const extrasTotal = data.extraItems.reduce((n, e) => n + e.amount * e.quantity, 0);
  const total = regFee + sessionFee + extrasTotal;

  if (sent) {
    return (
      <div className="max-w-2xl mx-auto p-6 flex flex-col items-center justify-center py-24 space-y-5 text-center">
        <div className="w-16 h-16 rounded-full bg-olive/10 flex items-center justify-center">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-olive">
            <path d="M5 12.5 10 17l9-10" />
          </svg>
        </div>
        <div>
          <h2 className="text-xl font-bold">Invoice Sent!</h2>
          <p className="text-text-muted text-sm mt-1">
            Invoice <span className="font-mono font-semibold">{data.invoiceNumber}</span> has been sent to{' '}
            <span className="font-semibold">{data.email || data.parentName}</span>
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="primary" onClick={onCreateNew}>+ Create New Invoice</Button>
          {onViewHistory && (
            <Button onClick={onViewHistory}>View Invoice History →</Button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto p-6 space-y-5">
      {/* Action bar */}
      <div className="flex items-center justify-between">
        <Button onClick={onBack} disabled={sending}>← Back to Form</Button>
        <Button variant="primary" onClick={onSend} disabled={sending}>
          {sending ? 'Saving…' : 'Send Invoice →'}
        </Button>
      </div>

      {/* Invoice document — matches Sunny's format */}
      <div className="bg-white border border-border rounded-xl shadow-card overflow-hidden text-sm" id="invoice-doc">

        {/* Top header bar with logo area */}
        <div className="px-10 pt-8 pb-4 flex items-start justify-between">
          <img
            src="/Shichida India logo.png"
            alt="Shichida India"
            className="h-20 w-auto object-contain"
          />
          <div />
        </div>

        {/* INVOICE title */}
        <div className="px-10 pb-4 text-center">
          <div className="text-3xl font-bold tracking-widest text-charcoal">INVOICE</div>
        </div>

        {/* Invoice meta — top right */}
        <div className="px-10 pb-6 flex justify-end">
          <div className="text-right text-sm space-y-0.5">
            <div>Invoice #: <span className="font-semibold">{data.invoiceNumber}</span></div>
            <div>Date: {fmtDate(data.invoiceDate)}</div>
            <div>Due Date: {fmtDate(data.dueDate)}</div>
          </div>
        </div>

        {/* BILL TO */}
        <div className="px-10 pb-6">
          <div className="text-[#1a5fa8] font-bold text-sm mb-2 uppercase tracking-wide">Bill To</div>
          <div className="space-y-0.5 text-sm">
            <div>Student: <span className="font-medium">{data.studentName}</span></div>
            <div>Parent/Guardian: <span className="font-medium">{data.parentName}</span></div>
            <div>Center: <span className="font-medium">{data.centerCode}</span></div>
            {data.city && <div>City: <span className="font-medium">{data.city}</span></div>}
            {data.contact && <div>Contact: <span className="font-medium">{data.contact}</span></div>}
            {data.email && <div>Email: <span className="font-medium">{data.email}</span></div>}
          </div>
        </div>

        {/* REGISTRATION DETAILS table */}
        <div className="px-10 pb-6">
          <div className="text-[#1a5fa8] font-bold text-sm mb-3 uppercase tracking-wide">
            Registration Details
          </div>
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="bg-gray-50">
                <th className="border border-gray-300 px-4 py-2 text-left font-semibold">Description</th>
                <th className="border border-gray-300 px-4 py-2 text-center font-semibold w-24">Quantity</th>
                <th className="border border-gray-300 px-4 py-2 text-right font-semibold w-32">Amount</th>
              </tr>
            </thead>
            <tbody>
              {regFee > 0 && (
                <tr>
                  <td className="border border-gray-300 px-4 py-2 font-medium">Registration Fee</td>
                  <td className="border border-gray-300 px-4 py-2 text-center">1</td>
                  <td className="border border-gray-300 px-4 py-2 text-right">{formatINR(regFee)}</td>
                </tr>
              )}
              {(data.sessionFeeStart || data.sessionFeeEnd || sessionFee > 0) && (
                <tr>
                  <td className="border border-gray-300 px-4 py-2 font-medium">
                    Session fee for the period<br />
                    <span className="font-normal">
                      {fmtPeriodDate(data.sessionFeeStart)} to {fmtPeriodDate(data.sessionFeeEnd)}
                    </span>
                  </td>
                  <td className="border border-gray-300 px-4 py-2 text-center">1</td>
                  <td className="border border-gray-300 px-4 py-2 text-right">{formatINR(sessionFee)}</td>
                </tr>
              )}
              {data.extraItems
                .filter((e) => e.description || e.amount > 0)
                .map((e) => (
                  <tr key={e.id}>
                    <td className="border border-gray-300 px-4 py-2">{e.description}</td>
                    <td className="border border-gray-300 px-4 py-2 text-center">{e.quantity}</td>
                    <td className="border border-gray-300 px-4 py-2 text-right">{formatINR(e.amount * e.quantity)}</td>
                  </tr>
                ))}
            </tbody>
            <tfoot>
              <tr className="bg-gray-50">
                <td className="border border-gray-300 px-4 py-2" colSpan={2}>
                  <span className="font-bold">TOTAL</span>
                </td>
                <td className="border border-gray-300 px-4 py-2 text-right font-bold">
                  {formatINR(total)}
                </td>
              </tr>
            </tfoot>
          </table>
        </div>

        {/* PAYMENT DETAILS */}
        {(data.bankName || data.accountNumber || data.ifscCode) && (
          <div className="px-10 pb-6">
            <div className="text-[#1a5fa8] font-bold text-sm mb-2 uppercase tracking-wide">
              Payment Details
            </div>
            <div className="space-y-0.5 text-sm">
              {data.bankName && <div>Bank: <span className="font-medium">{data.bankName}</span></div>}
              {data.accountNumber && <div>Account Number: <span className="font-medium">{data.accountNumber}</span></div>}
              {data.ifscCode && <div>IFSC Code: <span className="font-medium">{data.ifscCode}</span></div>}
            </div>
          </div>
        )}

        {/* Reference note */}
        <div className="px-10 pb-4 text-sm text-text-muted">
          Please reference your child full name or invoice number
        </div>

        {/* Thank you */}
        <div className="px-10 pb-6 text-center italic text-sm text-text-muted">
          Thank you for registering with Shichida India!
        </div>

        {/* Footer */}
        <div className="border-t border-gray-200 px-10 py-3 bg-gray-50 text-center text-xs text-text-dim">
          {COMPANY_LEGAL}
          {data.gstNumber && <span> GST Number : {data.gstNumber}</span>}
        </div>
      </div>
    </div>
  );
}

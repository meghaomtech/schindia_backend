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
  onBack,
  onCreateNew,
  onViewHistory,
}: {
  data: InvoiceFormData;
  sent: boolean;
  onBack: () => void;
  onCreateNew: () => void;
  onViewHistory?: () => void;
}) {
  const regFee = data.registrationFee ?? 0;
  const sessionFee = data.sessionFeeAmount ?? 0;
  const extrasTotal = data.extraItems.reduce((n, e) => n + e.amount * e.quantity, 0);
  const deductionsTotal = data.deductions.reduce((n, e) => n + e.amount * e.quantity, 0);
  const subtotal = regFee + sessionFee + extrasTotal - deductionsTotal;
  const gstPercent = data.gstPercent ?? 0;
  const gstAmount = Math.round(subtotal * gstPercent / 100);
  const debitBroughtForward = data.debitBroughtForward ?? 0;
  const total = subtotal + gstAmount + debitBroughtForward;

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

  function downloadInvoice() {
    const regFeeVal = data.registrationFee ?? 0;
    const sessionFeeVal = data.sessionFeeAmount ?? 0;
    const extrasTotalVal = data.extraItems.reduce((n, e) => n + e.amount * e.quantity, 0);
    const deductionsTotalVal = data.deductions.reduce((n, e) => n + e.amount * e.quantity, 0);
    const subtotalVal = regFeeVal + sessionFeeVal + extrasTotalVal - deductionsTotalVal;
    const gstPct = data.gstPercent ?? 0;
    const gstVal = Math.round(subtotalVal * gstPct / 100);
    const debitVal = data.debitBroughtForward ?? 0;
    const totalVal = subtotalVal + gstVal + debitVal;

    const fmtINR = (n: number) => `₹ ${n.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
    const fmtD = (iso: string) => {
      if (!iso) return '';
      const [y, m, d] = iso.split('-').map(Number);
      return `${String(d).padStart(2, '0')}/${String(m).padStart(2, '0')}/${y}`;
    };

    // Build table rows
    let rows = '';
    if (regFeeVal > 0) {
      rows += `<tr><td>Registration Fee</td><td class="center">1</td><td class="right">${fmtINR(regFeeVal)}</td></tr>`;
    }
    if (data.sessionFeeStart || data.sessionFeeEnd || sessionFeeVal > 0) {
      rows += `<tr><td>Session fee for the period<br/><span style="font-weight:normal">${fmtD(data.sessionFeeStart)} to ${fmtD(data.sessionFeeEnd)}</span></td><td class="center">1</td><td class="right">${fmtINR(sessionFeeVal)}</td></tr>`;
    }
    for (const e of data.extraItems.filter((x) => x.description || x.amount > 0)) {
      rows += `<tr><td>${e.description}</td><td class="center">${e.quantity}</td><td class="right">${fmtINR(e.amount * e.quantity)}</td></tr>`;
    }
    for (const e of data.deductions.filter((x) => x.description || x.amount > 0)) {
      rows += `<tr><td style="color:#dc2626">${e.description} (Credit)</td><td class="center">${e.quantity}</td><td class="right" style="color:#dc2626">- ${fmtINR(e.amount * e.quantity)}</td></tr>`;
    }

    // Footer rows
    let footerRows = '';
    if (gstPct > 0 || debitVal > 0) {
      footerRows += `<tr><td colspan="2">Subtotal</td><td class="right">${fmtINR(subtotalVal)}</td></tr>`;
      if (gstPct > 0) {
        footerRows += `<tr><td colspan="2">GST (${gstPct}%)</td><td class="right">${fmtINR(gstVal)}</td></tr>`;
      }
      if (debitVal > 0) {
        footerRows += `<tr><td colspan="2">Debit Brought Forward</td><td class="right">${fmtINR(debitVal)}</td></tr>`;
      }
    }
    footerRows += `<tr class="total-row"><td colspan="2"><strong>TOTAL</strong></td><td class="right"><strong>${fmtINR(totalVal)}</strong></td></tr>`;

    // Payment details
    let paymentHtml = '';
    if (data.bankName || data.accountNumber || data.ifscCode || data.upiId) {
      paymentHtml = `<div class="section"><div class="section-title">Payment Details</div><div class="info">`;
      if (data.bankName) paymentHtml += `<div>Bank: <strong>${data.bankName}</strong></div>`;
      if (data.accountNumber) paymentHtml += `<div>Account Number: <strong>${data.accountNumber}</strong></div>`;
      if (data.ifscCode) paymentHtml += `<div>IFSC Code: <strong>${data.ifscCode}</strong></div>`;
      if (data.upiId) paymentHtml += `<div>UPI ID: <strong>${data.upiId}</strong></div>`;
      paymentHtml += `</div></div>`;
    }

    const html = `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<title>Invoice ${data.invoiceNumber}</title>
<style>
  @page { size: A4; margin: 15mm; margin-bottom: 10mm; }
  @page { @bottom-left { content: ''; } @bottom-right { content: ''; } }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 13px; color: #1a1a1a; line-height: 1.5; }
  @media print {
    body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    title { display: none; }
  }
  .container { max-width: 100%; padding: 0; }
  .header { display: flex; justify-content: flex-start; margin-bottom: 20px; }
  .header img { height: 70px; }
  .invoice-title { text-align: center; font-size: 26px; font-weight: 700; letter-spacing: 0.15em; margin-bottom: 16px; }
  .meta { text-align: right; margin-bottom: 24px; font-size: 13px; }
  .meta div { margin-bottom: 2px; }
  .section { margin-bottom: 20px; }
  .section-title { color: #1a5fa8; font-weight: 700; font-size: 13px; text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 8px; }
  .info { font-size: 13px; line-height: 1.7; }
  .info strong { font-weight: 600; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; margin-bottom: 4px; }
  th, td { border: 1px solid #d1d5db; padding: 8px 12px; text-align: left; }
  th { background: #f9fafb; font-weight: 600; }
  .center { text-align: center; }
  .right { text-align: right; }
  .total-row { background: #f9fafb; }
  .note { font-size: 12px; color: #6b7280; margin-top: 16px; }
  .thankyou { text-align: center; font-style: italic; color: #6b7280; font-size: 13px; margin: 16px 0; }
  .footer { border-top: 1px solid #e5e7eb; padding-top: 10px; margin-top: 20px; text-align: center; font-size: 11px; color: #6b7280; }
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <img src="${window.location.origin}/Shichida India logo.png" alt="Shichida India"/>
  </div>
  <div class="invoice-title">INVOICE</div>
  <div class="meta">
    <div>Invoice #: <strong>${data.invoiceNumber}</strong></div>
    <div>Date: ${fmtD(data.invoiceDate)}</div>
    <div>Due Date: ${fmtD(data.dueDate)}</div>
  </div>
  <div class="section">
    <div class="section-title">Bill To</div>
    <div class="info">
      <div>Student: <strong>${data.studentName}</strong></div>
      <div>Parent/Guardian: <strong>${data.parentName}</strong></div>
      <div>Center: <strong>${data.centerCode}${data.centerLocation ? ` — ${data.centerLocation}` : ''}</strong></div>
      ${data.fullAddress ? `<div>Address: <strong>${data.fullAddress}</strong></div>` : ''}
      ${data.city ? `<div>City: <strong>${data.city}</strong></div>` : ''}
      ${data.contact ? `<div>Contact: <strong>${data.contact}</strong></div>` : ''}
      ${data.email ? `<div>Email: <strong>${data.email}</strong></div>` : ''}
    </div>
  </div>
  <div class="section">
    <div class="section-title">Registration Details</div>
    <table>
      <thead>
        <tr><th>Description</th><th class="center" style="width:80px">Quantity</th><th class="right" style="width:120px">Amount</th></tr>
      </thead>
      <tbody>${rows}</tbody>
      <tfoot>${footerRows}</tfoot>
    </table>
  </div>
  ${paymentHtml}
  <div class="note">Please reference your child full name or invoice number</div>
  <div class="thankyou">Thank you for registering with Shichida India!</div>
  <div class="footer">
    Shichida India licensed operating brand of Brain Astra Pvt Ltd. Company registration number CIN U72900KA2022PTC158571.${data.gstNumber ? ` GST Number: ${data.gstNumber}` : ''}
  </div>
</div>
</body>
</html>`;

    const printWindow = window.open('', '_blank');
    if (!printWindow) return;
    printWindow.document.write(html);
    printWindow.document.close();
    setTimeout(() => {
      printWindow.print();
      printWindow.close();
    }, 600);
  }

  return (
    <div className="max-w-2xl mx-auto p-6 space-y-5">
      {/* Action bar */}
      <div className="flex items-center justify-between">
        <Button onClick={onBack}>← Back to Form</Button>
        <Button type="button" onClick={downloadInvoice}>
          ⬇ Download PDF
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
            <div>Center: <span className="font-medium">{data.centerCode}{data.centerLocation ? ` — ${data.centerLocation}` : ''}</span></div>
            {data.fullAddress && <div>Address: <span className="font-medium">{data.fullAddress}</span></div>}
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
              {data.deductions
                .filter((e) => e.description || e.amount > 0)
                .map((e) => (
                  <tr key={e.id}>
                    <td className="border border-gray-300 px-4 py-2 text-red-600">{e.description} (Credit)</td>
                    <td className="border border-gray-300 px-4 py-2 text-center">{e.quantity}</td>
                    <td className="border border-gray-300 px-4 py-2 text-right text-red-600">- {formatINR(e.amount * e.quantity)}</td>
                  </tr>
                ))}
            </tbody>
            <tfoot>
              {(gstPercent > 0 || debitBroughtForward > 0) && (
                <>
                  <tr>
                    <td className="border border-gray-300 px-4 py-2" colSpan={2}>
                      Subtotal
                    </td>
                    <td className="border border-gray-300 px-4 py-2 text-right">
                      {formatINR(subtotal)}
                    </td>
                  </tr>
                  {gstPercent > 0 && (
                    <tr>
                      <td className="border border-gray-300 px-4 py-2" colSpan={2}>
                        GST ({gstPercent}%)
                      </td>
                      <td className="border border-gray-300 px-4 py-2 text-right">
                        {formatINR(gstAmount)}
                      </td>
                    </tr>
                  )}
                  {debitBroughtForward > 0 && (
                    <tr>
                      <td className="border border-gray-300 px-4 py-2" colSpan={2}>
                        Debit Brought Forward
                      </td>
                      <td className="border border-gray-300 px-4 py-2 text-right">
                        {formatINR(debitBroughtForward)}
                      </td>
                    </tr>
                  )}
                </>
              )}
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
        {(data.bankName || data.accountNumber || data.ifscCode || data.upiId) && (
          <div className="px-10 pb-6">
            <div className="text-[#1a5fa8] font-bold text-sm mb-2 uppercase tracking-wide">
              Payment Details
            </div>
            <div className="space-y-0.5 text-sm">
              {data.bankName && <div>Bank: <span className="font-medium">{data.bankName}</span></div>}
              {data.accountNumber && <div>Account Number: <span className="font-medium">{data.accountNumber}</span></div>}
              {data.ifscCode && <div>IFSC Code: <span className="font-medium">{data.ifscCode}</span></div>}
              {data.upiId && <div>UPI ID: <span className="font-medium">{data.upiId}</span></div>}
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

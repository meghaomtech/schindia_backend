import type { InvoiceFormData } from './invoiceGeneratorTypes';

const STORAGE_KEY = 'shichida_invoice_history';

export interface StoredInvoice {
  invoiceNumber: string;
  studentName: string;
  parentName: string;
  centerCode: string;
  centerLocation: string;
  invoiceDate: string;
  totalAmount: number;
  createdAt: string;
  data: InvoiceFormData;
}

function computeTotal(data: InvoiceFormData): number {
  const regFee = data.registrationFee ?? 0;
  const sessionFee = data.sessionFeeAmount ?? 0;
  const extrasTotal = data.extraItems.reduce((n, e) => n + e.amount * e.quantity, 0);
  const deductionsTotal = data.deductions.reduce((n, e) => n + e.amount * e.quantity, 0);
  const subtotal = regFee + sessionFee + extrasTotal - deductionsTotal;
  const gstPercent = data.gstPercent ?? 0;
  const gstAmount = Math.round(subtotal * gstPercent / 100);
  const debitBroughtForward = data.debitBroughtForward ?? 0;
  return subtotal + gstAmount + debitBroughtForward;
}

export function saveInvoiceLocally(data: InvoiceFormData): void {
  const history = loadInvoiceHistory();
  // Update if same invoice number exists, otherwise add
  const existing = history.findIndex((h) => h.invoiceNumber === data.invoiceNumber);
  const entry: StoredInvoice = {
    invoiceNumber: data.invoiceNumber,
    studentName: data.studentName,
    parentName: data.parentName,
    centerCode: data.centerCode,
    centerLocation: data.centerLocation,
    invoiceDate: data.invoiceDate,
    totalAmount: computeTotal(data),
    createdAt: new Date().toISOString(),
    data,
  };
  if (existing >= 0) {
    history[existing] = entry;
  } else {
    history.unshift(entry);
  }
  localStorage.setItem(STORAGE_KEY, JSON.stringify(history));
}

export function loadInvoiceHistory(): StoredInvoice[] {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '[]');
  } catch {
    return [];
  }
}

export function deleteInvoiceFromHistory(invoiceNumber: string): void {
  const history = loadInvoiceHistory().filter((h) => h.invoiceNumber !== invoiceNumber);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(history));
}

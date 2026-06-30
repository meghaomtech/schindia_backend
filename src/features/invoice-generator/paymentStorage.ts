const STORAGE_KEY = 'shichida_payments';

export interface Payment {
  id: string;
  invoiceNumber: string;
  studentName: string;
  parentName: string;
  centerCode: string;
  amount: number;
  paymentDate: string;
  paymentMode: 'cash' | 'upi' | 'bank_transfer' | 'cheque' | 'other';
  referenceNumber: string;
  notes: string;
  createdAt: string;
}

export function loadPayments(): Payment[] {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '[]');
  } catch {
    return [];
  }
}

export function savePayment(payment: Payment): void {
  const payments = loadPayments();
  payments.unshift(payment);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(payments));
}

export function deletePayment(id: string): void {
  const payments = loadPayments().filter((p) => p.id !== id);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(payments));
}

export function updatePayment(id: string, updated: Omit<Payment, 'id' | 'createdAt'>): void {
  const payments = loadPayments().map((p) =>
    p.id === id ? { ...p, ...updated } : p
  );
  localStorage.setItem(STORAGE_KEY, JSON.stringify(payments));
}

export function getPaymentsForInvoice(invoiceNumber: string): Payment[] {
  return loadPayments().filter((p) => p.invoiceNumber === invoiceNumber);
}

export function getTotalPaidForInvoice(invoiceNumber: string): number {
  return getPaymentsForInvoice(invoiceNumber).reduce((sum, p) => sum + p.amount, 0);
}

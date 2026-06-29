export interface SavedCenter {
  id: string;
  centerCode: string;
  bankName: string;
  accountNumber: string;
  ifscCode: string;
  gstNumber: string;
}

export interface ExtraLineItem {
  id: string;
  description: string;
  quantity: number;
  amount: number;
}

export interface InvoiceFormData {
  // Center / payment details (saveable)
  centerCode: string;
  bankName: string;
  accountNumber: string;
  ifscCode: string;
  gstNumber: string;

  // Student details
  studentName: string;
  parentName: string;
  city: string;
  contact: string;
  email: string;

  // Invoice meta
  invoiceNumber: string;
  invoiceDate: string;
  dueDate: string;

  // Registration line items
  registrationFee: number;
  sessionFeeStart: string;
  sessionFeeEnd: string;
  sessionFeeAmount: number;

  // Additional items
  extraItems: ExtraLineItem[];
}

export interface SavedCenter {
  id: string;
  centerCode: string;
  centerLocation: string;
  fullAddress: string;
  centerEmail: string;
  centerPhone: string;
  gstNumber: string;
  website: string;
  bankName: string;
  accountNumber: string;
  ifscCode: string;
  upiId: string;
}

export interface ExtraLineItem {
  id: string;
  description: string;
  quantity: number;
  amount: number;
}

export interface InvoiceFormData {
  // Center details (saveable)
  centerCode: string;
  centerLocation: string;
  fullAddress: string;
  centerEmail: string;
  centerPhone: string;
  gstNumber: string;
  website: string;

  // Bank details (saveable)
  bankName: string;
  accountNumber: string;
  ifscCode: string;
  upiId: string;

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
  gstPercent: number;
  debitBroughtForward: number;

  // Registration line items
  registrationFee: number;
  sessionFeeStart: string;
  sessionFeeEnd: string;
  sessionFeeAmount: number;

  // Extra charges
  extraItems: ExtraLineItem[];

  // Deductions / Credits
  deductions: ExtraLineItem[];
}

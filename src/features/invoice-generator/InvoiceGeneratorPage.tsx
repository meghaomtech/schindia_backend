import { useState } from 'react';
import { InvoiceForm, nextInvoiceNum } from './InvoiceForm';
import { InvoicePreview } from './InvoicePreview';
import type { InvoiceFormData } from './invoiceGeneratorTypes';

type Step = 'form' | 'preview' | 'sent';

const COMPANY_GST = '06AAKCB5662Q1Z0';

function todayISO(): string {
  return new Date().toISOString().slice(0, 10);
}

function tomorrowISO(): string {
  const d = new Date();
  d.setDate(d.getDate() + 1);
  return d.toISOString().slice(0, 10);
}

function defaultFormData(): InvoiceFormData {
  return {
    centerCode: '',
    bankName: '',
    accountNumber: '',
    ifscCode: '',
    gstNumber: COMPANY_GST,
    studentName: '',
    parentName: '',
    city: '',
    contact: '',
    email: '',
    invoiceNumber: nextInvoiceNum(),
    invoiceDate: todayISO(),
    dueDate: tomorrowISO(),
    registrationFee: 0,
    sessionFeeStart: '',
    sessionFeeEnd: '',
    sessionFeeAmount: 0,
    extraItems: [],
  };
}

export function InvoiceGeneratorPage() {
  const [step, setStep] = useState<Step>('form');
  const [formData, setFormData] = useState<InvoiceFormData>(defaultFormData);

  if (step === 'form') {
    return (
      <InvoiceForm
        data={formData}
        onChange={setFormData}
        onGenerate={() => setStep('preview')}
      />
    );
  }

  return (
    <InvoicePreview
      data={formData}
      sent={step === 'sent'}
      onBack={() => setStep('form')}
      onSend={() => setStep('sent')}
      onCreateNew={() => {
        setFormData(defaultFormData());
        setStep('form');
      }}
    />
  );
}
